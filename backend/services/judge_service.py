"""Real LLM-based judging service.

Replaces deterministic stub scoring with actual LLM evaluation of corps work.
Each caption judge gets a system prompt, the show prompt, and work artifacts,
then produces structured rep/perf scores + narrative feedback.
"""

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.agent_definition import ModelTier
from backend.models.score import JudgeType
from backend.services.llm_client import LLMClient, LLMMessage, LLMResponse
from backend.services.scoring_service import DEFAULT_WEIGHTS

logger = logging.getLogger(__name__)

ENABLE_REAL_JUDGING = os.environ.get("ENABLE_REAL_JUDGING", "1") == "1"


@dataclass
class JudgeContext:
    """Everything a judge needs to evaluate a corps performance."""
    corps_id: str
    show_slug: str
    show_prompt: str = ""
    spec_text: str = ""
    design_notes: str = ""
    work_logs: list[dict] = field(default_factory=list)
    agent_sessions: list[dict] = field(default_factory=list)
    corps_metadata: dict = field(default_factory=dict)
    rep_results: list[dict] = field(default_factory=list)
    # Artifact completeness: 0.0 (nothing produced) to 1.0 (all expected artifacts present)
    artifact_completeness: float = 0.0
    artifact_details: dict = field(default_factory=dict)


@dataclass
class JudgeResult:
    """Result from a single caption judge."""
    judge_type: JudgeType
    rep_score: float = 0.0
    perf_score: float = 0.0
    feedback: str = ""
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)

    @property
    def total_score(self) -> float:
        return (self.rep_score + self.perf_score) / 2


# System prompts per caption
JUDGE_PROMPTS: dict[JudgeType, str] = {
    JudgeType.GENERAL_EFFECT: """You are a DCI General Effect judge evaluating an AI agent corps' performance.
Assess: How well did the final product match the show prompt's intent? Was the overall vision realized?
Consider: creative interpretation, completeness of deliverables, alignment with stated goals, user experience quality.
""",
    JudgeType.VISUAL: """You are a DCI Visual judge evaluating an AI agent corps' performance.
Assess: UI/UX quality, documentation quality, visual coherence, code formatting and organization.
Consider: readability, consistency, naming conventions, file organization, README quality, output presentation.
""",
    JudgeType.GUARD: """You are a DCI Guard (Color Guard) judge evaluating an AI agent corps' performance.
Assess: Security, error handling, edge case coverage, defensive programming.
Consider: input validation, error messages, graceful degradation, security best practices, robustness.
""",
    JudgeType.BRASS: """You are a DCI Brass judge evaluating an AI agent corps' performance.
Assess: Code quality, correctness, architecture, algorithmic soundness.
Consider: design patterns, separation of concerns, DRY principle, type safety, performance, correctness.
""",
    JudgeType.PERCUSSION: """You are a DCI Percussion judge evaluating an AI agent corps' performance.
Assess: Test coverage, reliability, robustness, CI/CD readiness.
Consider: test quality, edge case testing, integration tests, error recovery, reproducibility.
""",
    JudgeType.ENSEMBLE_TECHNIQUE: """You are a DCI Ensemble Technique judge evaluating an AI agent corps' performance.
Assess: Did the ED delegate effectively? Process quality, agent utilization, collaboration patterns.
Consider: task breakdown, parallel work, communication efficiency, role clarity, bottleneck avoidance, rework rate.
""",
}

JUDGE_OUTPUT_INSTRUCTION = """
Output your evaluation as JSON with exactly these fields:
{
  "rep_score": <0-100 integer — repertoire/content quality>,
  "perf_score": <0-100 integer — execution/performance quality>,
  "feedback": "<2-3 sentence narrative assessment>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "weaknesses": ["<weakness 1>", "<weakness 2>"],
  "action_items": ["<specific improvement 1>", "<specific improvement 2>"]
}

USE THE FULL 0-100 SCALE. Differentiate aggressively. Scores should span at least
a 30-point range across corps — do NOT cluster all scores in a narrow band.

SCORING ANCHORS — your scores MUST match your narrative:
- 90-100: Championship-caliber. All deliverables complete, tested, polished, innovative.
          Only award this for truly exceptional, production-ready work.
- 80-89: Strong execution. Most deliverables implemented and working. Minor gaps only.
         Code runs, tests pass, docs are clear.
- 70-79: Solid partial execution. Multiple deliverables built and functional.
         Some gaps but clear evidence of working code/features.
- 60-69: Mixed results. Some code written but significant gaps remain.
         Plans exist with limited execution evidence.
- 50-59: Planning only. Specs and designs exist but NO working implementation.
         A good spec with zero code = 55 max.
- 40-49: Minimal planning, no execution. Incomplete specs, no deliverables.
- 30-39: Barely started. Scaffolding files present but empty or trivial content.
- 20-29: Almost nothing produced. Boilerplate only.
- Below 20: No meaningful work.

HARD RULES:
1. Having spec.md + design_notes.md does NOT earn above 59. Files existing ≠ execution.
2. If your narrative says "missing execution" or "no concrete artifacts," perf MUST be below 50.
3. Scores above 70 require EVIDENCE of working code, tests, or functional features.
4. perf_score should always be LOWER than rep_score when execution lags behind planning.
5. A 15+ point gap between rep and perf is expected when plans are good but execution is weak.

rep_score = quality of the CONTENT/PLAN (the "what"). Good plans earn 50-70.
perf_score = quality of the EXECUTION/DELIVERY (the "how well").
  - Nothing built: 20-35
  - Partial scaffolding: 35-50
  - Some working features: 50-70
  - Most features working: 70-85
  - Everything polished: 85-100

Output ONLY the JSON object, no other text.
"""


def build_judge_context(
    db: Session,
    corps_id: str,
    show_slug: str,
) -> JudgeContext:
    """Build the full context a judge needs to evaluate a corps."""
    from pathlib import Path
    from backend.models.work_log import WorkLog
    from backend.models.agent_session import AgentSession
    from backend.models.corps import Corps

    ctx = JudgeContext(corps_id=corps_id, show_slug=show_slug)

    # Load show artifacts from filesystem
    root = Path(os.environ.get("DCI_ROOT", "."))
    show_dir = root / "shows" / show_slug

    prompt_path = show_dir / "show_prompt.md"
    if prompt_path.exists():
        ctx.show_prompt = prompt_path.read_text()[:8000]

    spec_path = show_dir / "spec.md"
    if spec_path.exists():
        ctx.spec_text = spec_path.read_text()[:6000]

    notes_path = show_dir / "design_notes.md"
    if notes_path.exists():
        ctx.design_notes = notes_path.read_text()[:4000]

    # Corps metadata from DB
    corps = db.query(Corps).filter(Corps.id == corps_id).first()
    if corps:
        ctx.corps_metadata = {
            "display_name": corps.name,
            "status": corps.status.value if corps.status else "unknown",
            "theme": getattr(corps, "theme", None),
        }

    # Work logs (last 50)
    logs = (
        db.query(WorkLog)
        .filter(WorkLog.corps_id == corps_id)
        .order_by(WorkLog.timestamp.desc())
        .limit(50)
        .all()
    )
    ctx.work_logs = [
        {
            "role": log.role,
            "event_type": log.event_type,
            "summary": (log.details or "")[:200],
        }
        for log in logs
    ]

    # Agent sessions (last 20)
    sessions = (
        db.query(AgentSession)
        .filter(AgentSession.corps_id == corps_id)
        .order_by(AgentSession.started_at.desc())
        .limit(20)
        .all()
    )
    ctx.agent_sessions = [
        {
            "role": getattr(s, "role", "unknown"),
            "status": s.status.value if hasattr(s.status, "value") else str(s.status),
            "iterations": getattr(s, "iterations", 0),
        }
        for s in sessions
    ]

    # Compute artifact completeness — what did the corps actually produce?
    # Separate planning artifacts (scaffolding) from execution artifacts (real work)
    completed_sessions = sum(
        1 for s in ctx.agent_sessions if s["status"] == "completed"
    )
    execution_logs = sum(
        1 for log in ctx.work_logs
        if log["event_type"] in ("agent_complete", "tool_success", "rep_completed")
    )
    artifact_checks = {
        "has_spec": bool(ctx.spec_text and ctx.spec_text.strip()),
        "has_show_prompt": bool(ctx.show_prompt and ctx.show_prompt.strip()),
        "has_design_notes": bool(ctx.design_notes and len(ctx.design_notes.strip()) > 50),
        "has_work_logs": len(ctx.work_logs) > 0,
        "has_active_agents": any(
            s["status"] in ("active", "completed") for s in ctx.agent_sessions
        ),
        # Execution indicators (weighted higher)
        "has_substantial_sessions": completed_sessions >= 5,
        "has_execution_evidence": execution_logs >= 3,
    }
    ctx.artifact_details = artifact_checks
    # Weight execution indicators higher: planning checks worth 1, execution worth 2
    planning_score = sum(1 for k, v in artifact_checks.items()
                         if v and k.startswith("has_") and k not in ("has_substantial_sessions", "has_execution_evidence"))
    execution_score = sum(2 for k, v in artifact_checks.items()
                          if v and k in ("has_substantial_sessions", "has_execution_evidence"))
    max_score = 5 + 4  # 5 planning + 2*2 execution
    ctx.artifact_completeness = (planning_score + execution_score) / max_score

    return ctx


def _build_judge_user_message(context: JudgeContext) -> str:
    """Build the user message containing all artifacts for evaluation."""
    parts = [f"## Show: {context.show_slug}\n## Corps: {context.corps_metadata.get('display_name', context.corps_id)}\n"]

    # Artifact completeness report — judges must factor this in
    pct = int(context.artifact_completeness * 100)
    parts.append(f"### Artifact Completeness: {pct}%")
    for check, present in context.artifact_details.items():
        status = "PRESENT" if present else "MISSING"
        parts.append(f"  - {check}: {status}")
    if context.artifact_completeness < 0.4:
        parts.append("\n**WARNING: This corps has produced minimal or no artifacts. "
                     "Score accordingly — missing work should result in perf_score below 40 "
                     "and rep_score below 55.**\n")
    elif context.artifact_completeness < 0.6:
        parts.append("\n**NOTE: This corps has planning artifacts but limited execution evidence. "
                     "Having specs/designs without working code caps perf_score at 50 max.**\n")
    parts.append("")

    if context.show_prompt:
        parts.append(f"### Show Prompt\n{context.show_prompt}\n")
    elif context.spec_text:
        parts.append(f"### Show Spec\n{context.spec_text}\n")

    if context.design_notes:
        parts.append(f"### Design Notes (excerpt)\n{context.design_notes[:2000]}\n")

    if context.work_logs:
        parts.append("### Recent Work Activity")
        for log in context.work_logs[:20]:
            parts.append(f"- [{log['role']}] {log['event_type']}: {log['summary']}")
        parts.append("")

    if context.agent_sessions:
        parts.append("### Agent Sessions")
        for s in context.agent_sessions[:10]:
            parts.append(f"- {s['role']}: {s['status']} ({s['iterations']} iterations)")
        parts.append("")

    return "\n".join(parts)


def _parse_judge_response(response_text: str, judge_type: JudgeType) -> JudgeResult:
    """Parse LLM JSON response into a JudgeResult."""
    result = JudgeResult(judge_type=judge_type)

    # Try to extract JSON from the response
    text = response_text.strip()
    # Handle markdown code blocks
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                text = part
                break

    try:
        data = json.loads(text)
        result.rep_score = max(0, min(100, float(data.get("rep_score", 70))))
        result.perf_score = max(0, min(100, float(data.get("perf_score", 70))))
        result.feedback = str(data.get("feedback", ""))
        result.strengths = list(data.get("strengths", []))
        result.weaknesses = list(data.get("weaknesses", []))
        result.action_items = list(data.get("action_items", []))
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning("Failed to parse judge response for %s: %s", judge_type.value, e)
        # Fallback: conservative middle-range scores (not optimistic 70)
        result.rep_score = 45.0
        result.perf_score = 35.0
        result.feedback = f"Judge response could not be parsed: {response_text[:200]}"

    return result


def invoke_judge(
    judge_type: JudgeType,
    context: JudgeContext,
    llm_client: LLMClient,
) -> JudgeResult:
    """Single-shot LLM call for one caption judge."""
    system_prompt = JUDGE_PROMPTS.get(judge_type, "You are a judge evaluating AI agent work.")
    user_message = _build_judge_user_message(context)

    messages = [
        LLMMessage(role="system", content=system_prompt + JUDGE_OUTPUT_INSTRUCTION),
        LLMMessage(role="user", content=user_message),
    ]

    try:
        response: LLMResponse = llm_client.chat(messages, model_tier=ModelTier.HAIKU)
        return _parse_judge_response(response.content, judge_type)
    except Exception as e:
        logger.error("Judge %s failed: %s", judge_type.value, e)
        return _stub_judge_result(judge_type, context.corps_id, context.show_slug)


def _stub_judge_result(
    judge_type: JudgeType,
    corps_id: str,
    show_slug: str,
    artifact_completeness: float = 1.0,
) -> JudgeResult:
    """Deterministic fallback scores when LLM is unavailable.

    Scores are scaled by artifact_completeness (0.0-1.0).
    Rep score (content quality): specs/plans present = higher rep.
    Perf score (execution quality): actual deliverables present = higher perf.

    Without any implementation artifacts, perf stays very low regardless of specs.
    """
    import hashlib
    seed = hashlib.sha256(f"{corps_id}:{show_slug}:{judge_type.value}".encode()).hexdigest()

    # Rep score: 50-75 range scaled by completeness (plans/specs exist?)
    raw_rep = (int(seed[:8], 16) % 25) + 50
    # Perf score: 30-60 range scaled more aggressively (was work actually done?)
    raw_perf = (int(seed[8:16], 16) % 30) + 30

    # Scale by artifact completeness: floor of 20
    floor = 20
    rep_score = floor + (raw_rep - floor) * artifact_completeness
    # Perf is harder to earn — completeness < 0.6 means no real execution
    perf_floor = 15
    perf_scale = max(0.0, (artifact_completeness - 0.4) / 0.6) if artifact_completeness > 0.4 else 0.0
    perf_score = perf_floor + (raw_perf - perf_floor) * perf_scale

    if artifact_completeness < 0.2:
        feedback = "Stub score — corps produced no meaningful artifacts."
    elif artifact_completeness < 0.6:
        feedback = "Stub score — specs/plans present but no implementation evidence. Perf scored low."
    elif artifact_completeness < 0.8:
        feedback = "Stub score — partial work produced. LLM judging unavailable for detailed assessment."
    else:
        feedback = "Stub score — LLM judging unavailable."

    return JudgeResult(
        judge_type=judge_type,
        rep_score=float(rep_score),
        perf_score=float(perf_score),
        feedback=feedback,
    )


def judge_corps_performance(
    db: Session,
    corps_id: str,
    show_slug: str,
    llm_client: Optional[LLMClient] = None,
) -> dict[JudgeType, JudgeResult]:
    """Run all caption judges for a corps performance. Returns dict of results."""
    context = build_judge_context(db, corps_id, show_slug)

    judge_types = [jt for jt in DEFAULT_WEIGHTS if jt != JudgeType.TIMING]
    completeness = context.artifact_completeness

    # If real judging disabled or no LLM client, use stubs
    if not ENABLE_REAL_JUDGING or llm_client is None:
        return {
            jt: _stub_judge_result(jt, corps_id, show_slug, completeness)
            for jt in judge_types
        }

    results: dict[JudgeType, JudgeResult] = {}

    # Run judges in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(invoke_judge, jt, context, llm_client): jt
            for jt in judge_types
        }
        for future in as_completed(futures):
            jt = futures[future]
            try:
                results[jt] = future.result()
            except Exception as e:
                logger.error("Judge %s raised: %s", jt.value, e)
                results[jt] = _stub_judge_result(jt, corps_id, show_slug, completeness)

    return results


def generate_judges_tape(
    db: Session,
    competition_id: str,
    corps_id: str,
    llm_client: Optional[LLMClient] = None,
) -> "JudgesTape":
    """Consolidate all caption scores + feedback into a JudgesTape record."""
    from backend.models.judges_tape import JudgesTape
    from backend.models.score import Score

    # Get all scores for this corps (most recent competition scores)
    scores = (
        db.query(Score)
        .filter(Score.corps_id == corps_id)
        .order_by(Score.created_at.desc())
        .limit(20)
        .all()
    )

    caption_feedbacks = {}
    for s in scores:
        jt = s.judge_type.value if hasattr(s.judge_type, "value") else str(s.judge_type)
        if jt not in caption_feedbacks:
            caption_feedbacks[jt] = {
                "value": s.value,
                "rep_score": s.rep_score,
                "perf_score": s.perf_score,
                "feedback": s.feedback or "",
                "box": s.box,
            }

    # Generate overall assessment via LLM if available
    overall = ""
    if llm_client and caption_feedbacks:
        feedback_text = "\n".join(
            f"- {jt}: {info['value']:.1f} — {info['feedback']}"
            for jt, info in caption_feedbacks.items()
        )
        messages = [
            LLMMessage(role="system", content="You are a chief judge synthesizing caption feedback into a 2-paragraph overall assessment. Be specific and constructive."),
            LLMMessage(role="user", content=f"Corps: {corps_id}\nCompetition: {competition_id}\n\nCaption feedback:\n{feedback_text}\n\nWrite a 2-paragraph overall assessment."),
        ]
        try:
            resp = llm_client.chat(
                messages,
                model_tier=ModelTier.HAIKU,
                batchable=True,
                workload="scoring_calculation",
                allow_deferred=True,
            )
            if resp.stop_reason != "queued":
                overall = resp.content.strip()
        except Exception as e:
            logger.warning("Overall assessment generation failed: %s", e)

    if not overall:
        # Fallback: mechanical summary
        avg = sum(info["value"] for info in caption_feedbacks.values()) / max(1, len(caption_feedbacks))
        overall = f"Average score across {len(caption_feedbacks)} captions: {avg:.1f}."

    tape = JudgesTape(
        competition_id=competition_id,
        corps_id=corps_id,
        caption_feedbacks=caption_feedbacks,
        overall_assessment=overall,
    )
    db.add(tape)
    db.commit()
    db.refresh(tape)
    return tape


def export_tape_markdown(tape: "JudgesTape") -> str:
    """Format a JudgesTape as readable markdown."""
    from datetime import timezone
    lines = [
        f"# Judges Tape",
        f"**Competition:** {tape.competition_id}",
        f"**Corps:** {tape.corps_id}",
        f"**Generated:** {tape.created_at}",
        "",
        "## Overall Assessment",
        "",
        tape.overall_assessment or "No assessment available.",
        "",
        "## Caption Scores",
        "",
    ]

    for jt, info in (tape.caption_feedbacks or {}).items():
        title = jt.replace("_", " ").title()
        rep = info.get("rep_score")
        perf = info.get("perf_score")
        lines.append(f"### {title}")
        lines.append(f"**Score:** {info.get('value', 0):.1f} (Box {info.get('box', 0)})")
        if rep is not None and perf is not None:
            lines.append(f"**Rep:** {rep:.1f} | **Perf:** {perf:.1f}")
        if info.get("feedback"):
            lines.append(f"> {info['feedback']}")
        lines.append("")

    return "\n".join(lines)
