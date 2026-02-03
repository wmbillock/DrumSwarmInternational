"""V1 API routes for corps management.

Extracted from router.py — all business logic lives in backend/services/.
"""

import json
import logging
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func

from backend.api.v1.helpers import (
    _get_root,
    _validate_id,
    _get_db_session,
    _generate_color_scheme,
)
from backend.services.yaml_util import safe_load_yaml_dict
from backend.api.v1.schemas import (
    GenerateIconRequest,
    CreateCorpsRequest,
    CorpsFeedbackRequest,
    CorpsThemeUpdateRequest,
    CorpsCommandRequest,
    CorpsModeSwitchRequest,
    RehearsalModeSetRequest,
    HireStaffRequest,
    ReleaseStaffRequest,
    MessageCreateV1Request,
    CritiqueClarifyRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_CORPS = 18  # DCI semifinals cap

_UNIFORM_STYLES = [
    "Military-inspired with braided epaulettes and sash",
    "Sleek modern design with asymmetric color blocking",
    "Classic corps style with plumed shako and gauntlets",
    "Contemporary athleisure with gradient panels",
    "Renaissance-inspired with tabard and metallic accents",
    "Space-age futuristic with reflective piping",
    "Western cavalry motif with fringe and concho details",
    "Art deco geometric patterns with gold trim",
    "Japanese-inspired hakama silhouette with obi sash",
    "Steampunk Victorian with brass fittings and goggles",
]

_ICON_THEMES = [
    "heraldic shield", "winged emblem", "celestial star burst",
    "crossed instruments", "flame and laurel wreath", "geometric mandala",
    "stylized animal crest", "art nouveau flourish", "modernist abstract mark",
    "military insignia with musical notation",
]

CORPS_COMMANDS = {
    "resume_hut": {"label": "Resume, Hut!", "description": "Wake all agents and begin/resume work", "category": "control"},
    "attention": {"label": "Attention!", "description": "All agents pause and report current status", "category": "control"},
    "at_ease": {"label": "At Ease", "description": "Finish current tasks then idle", "category": "control"},
    "dismissed": {"label": "Dismissed", "description": "Stop all agents, disband the corps", "category": "control"},
    "basics": {"label": "Basics", "description": "Switch to basics rehearsal mode (manual override)", "category": "rehearsal"},
    "sectionals": {"label": "Sectionals", "description": "Switch to sectionals rehearsal mode (manual override)", "category": "rehearsal"},
    "full_ensemble": {"label": "Full Ensemble", "description": "Switch to full ensemble rehearsal (manual override)", "category": "rehearsal"},
    "run_through": {"label": "Run Through", "description": "Full run-through rehearsal mode (manual override)", "category": "rehearsal"},
    "go_on_tour": {"label": "Go On Tour", "description": "Autonomous execution — agents work independently", "category": "execution"},
    "return_to_camps": {"label": "Return to Camps", "description": "Back to planning phase", "category": "execution"},
    "metronome_tick": {"label": "Metronome Tick", "description": "Manual metronome tick — reclaim stale work", "category": "system"},
    "merge_check": {"label": "Merge Check", "description": "Check and merge completed work", "category": "system"},
}


def _find_critique_file(root: Path, corps_id: str, round_num: int) -> Optional[Path]:
    seasons_dir = root / "seasons"
    if not seasons_dir.exists():
        return None
    matches: list[Path] = []
    for season_dir in seasons_dir.iterdir():
        if not season_dir.is_dir():
            continue
        perf_dir = season_dir / "performances" / corps_id
        if not perf_dir.is_dir():
            continue
        critique_path = perf_dir / f"critique_round_{round_num}.md"
        if critique_path.is_file():
            matches.append(critique_path)
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)


# =========================================================================
# CORPS LIST / CREATE
# =========================================================================


@router.get("/corps")
def v1_list_corps(include_system: bool = False):
    """List all corps from filesystem workspaces + DB, deduplicated by display_name."""
    root = _get_root()
    corps_base = root / "corps"
    result = []
    seen_names: set[str] = set()

    # Filesystem corps
    if corps_base.exists():
        for corps_dir in sorted(corps_base.iterdir()):
            corps_path = corps_dir / "corps.yaml"
            if not corps_path.is_file():
                continue
            try:
                data = safe_load_yaml_dict(corps_path.read_text())
                name = data.get("display_name", corps_dir.name)
                seen_names.add(name)
                result.append({
                    "corps_id": data.get("corps_id", corps_dir.name),
                    "display_name": name,
                    "philosophy": data.get("philosophy", ""),
                    "state": data.get("state", "unknown"),
                    "corps_type": data.get("corps_type", "competing"),
                })
            except Exception as e:
                logger.warning("Failed to read corps.yaml at %s: %s", corps_path, e)
                continue

    # DB corps (merge, dedup by display_name)
    try:
        from backend.models.corps import Corps, CorpsStatus
        from backend.models.agent_definition import AgentDefinition
        db = _get_db_session()
        try:
            query = db.query(Corps).filter(Corps.status != CorpsStatus.DISBANDED)
            if not include_system:
                query = query.filter(
                    (Corps.corps_type != "system") | (Corps.corps_type.is_(None))
                )
            db_corps = query.all()
            staff_counts = {
                c_id: count
                for c_id, count in db.query(
                    AgentDefinition.corps_id, func.count(AgentDefinition.id)
                ).group_by(AgentDefinition.corps_id)
            }
            for c in db_corps:
                if c.name not in seen_names:
                    seen_names.add(c.name)
                    result.append({
                        "corps_id": c.id,
                        "display_name": c.name,
                        "philosophy": "",
                        "state": c.status.value if c.status else "unknown",
                        "corps_type": c.corps_type or "competing",
                        "theme_id": c.theme_id,
                        "mascot": c.mascot,
                        "staff_count": staff_counts.get(c.id, 0),
                    })
        finally:
            db.close()
    except Exception:
        pass  # DB unavailable — filesystem-only mode

    return result


@router.post("/corps/generate-identity")
def v1_generate_corps_identity():
    """Auto-generate a complete corps identity for preview."""
    from backend.services.nickname_generator import generate_corps_name, generate_mascot
    import json as _json

    # Gather existing names to avoid duplicates
    existing_names: set[str] = set()
    try:
        from backend.models.corps import Corps
        db = _get_db_session()
        try:
            for c in db.query(Corps.name).all():
                existing_names.add(c[0])
        finally:
            db.close()
    except Exception:
        pass

    name = generate_corps_name(existing_names)
    mascot = generate_mascot(existing_names)
    colors = _generate_color_scheme(name)

    uniform = random.choice(_UNIFORM_STYLES)
    icon_theme = random.choice(_ICON_THEMES)

    icon_prompt = (
        f"Design a {icon_theme} logo for a drum corps called '{name}' "
        f"with mascot '{mascot}'. Use colors: {colors['primary']}, "
        f"{colors['secondary']}, and {colors['accent']}. "
        f"Style: clean vector art, suitable for embroidery on uniforms. "
        f"No text in the image."
    )

    return {
        "name": name,
        "mascot": mascot,
        "color_scheme": colors,
        "uniform_concept": uniform,
        "icon_theme": icon_theme,
        "icon_prompt": icon_prompt,
    }


@router.post("/corps/generate-icon")
def v1_generate_corps_icon(req: GenerateIconRequest):
    """Use ChatGPT CLI to generate an icon description or image."""
    import shutil
    if not shutil.which("chatgpt"):
        return {
            "source": "fallback",
            "description": (
                "A bold heraldic emblem rendered in the corps colors, "
                "featuring the mascot in a dynamic pose surrounded by "
                "musical motifs and geometric framing."
            ),
            "image_url": None,
        }

    from backend.services.llm_client import ChatGPTCLIClient, LLMMessage
    from backend.models.agent_definition import ModelTier
    client = ChatGPTCLIClient()
    resp = client.chat(
        messages=[
            LLMMessage(role="system", content=(
                "You are a visual designer. Describe a corps logo based on the prompt. "
                "Output a vivid 2-3 sentence description of the logo design. "
                "If you can generate an image, include the URL."
            )),
            LLMMessage(role="user", content=req.icon_prompt),
        ],
        model_tier=ModelTier.SONNET,
    )
    return {
        "source": "chatgpt",
        "description": resp.content,
        "image_url": None,
    }


@router.post("/corps")
def v1_create_corps(req: CreateCorpsRequest):
    """Create a new corps via the DB. Enforces an 18-corps cap."""
    from backend.models.corps import Corps, CorpsStatus, CorpsMode
    from backend.services.corps_service import initialize_corps
    import json as _json

    db = _get_db_session()
    try:
        active_count = db.query(Corps).filter(
            Corps.status != CorpsStatus.DISBANDED
        ).count()
        if active_count >= MAX_CORPS:
            raise HTTPException(400, f"Maximum of {MAX_CORPS} active corps reached")

        # Check for name uniqueness
        existing = db.query(Corps).filter(Corps.name == req.name).first()
        if existing:
            raise HTTPException(409, f"Corps '{req.name}' already exists")

        import uuid
        corps_id = str(uuid.uuid4())

        # Store color scheme + uniform concept together
        theme_data = {}
        if req.color_scheme:
            theme_data["color_scheme"] = req.color_scheme
        if req.uniform_concept:
            theme_data["uniform_concept"] = req.uniform_concept

        corps = Corps(
            id=corps_id,
            name=req.name,
            status=CorpsStatus.WINTER_CAMPS,
            mode=CorpsMode.DESIGN_ROOM,
            mascot=req.mascot,
            uniform_concept=_json.dumps(theme_data) if theme_data else None,
        )
        db.add(corps)
        db.commit()
        initialize_corps(db, corps_id)

        return {
            "corps_id": corps_id,
            "display_name": req.name,
            "mascot": req.mascot,
            "color_scheme": req.color_scheme,
            "uniform_concept": req.uniform_concept,
            "philosophy": req.philosophy or "",
            "state": "winter_camps",
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to create corps: {e}")
    finally:
        db.close()


@router.get("/corps/{corps_id}/staffing-status")
def v1_get_corps_staffing_status(corps_id: str):
    """Return staffing progress for a corps."""
    _validate_id(corps_id, "corps_id")
    from backend.services.corps_service import get_staffing_status

    db = _get_db_session()
    try:
        return get_staffing_status(db, corps_id)
    finally:
        db.close()


# =========================================================================
# CORPS DETAIL
# =========================================================================


@router.get("/corps/{corps_id}")
def v1_get_corps(corps_id: str):
    """Get corps detail including roster size and history. Falls back to DB for UUID lookups."""
    _validate_id(corps_id, "corps_id")
    root = _get_root()
    corps_path = root / "corps" / corps_id / "corps.yaml"
    if corps_path.is_file():
        data = safe_load_yaml_dict(corps_path.read_text())
        roster_path = root / "corps" / corps_id / "roster.yaml"
        roster_size = 0
        if roster_path.is_file():
            roster = safe_load_yaml_dict(roster_path.read_text())
            roster_size = len(roster.get("assignments", []))
        history = data.get("history", [])
        return {
            "corps_id": data.get("corps_id", corps_id),
            "display_name": data.get("display_name", corps_id),
            "philosophy": data.get("philosophy", ""),
            "state": data.get("state", "unknown"),
            "roster_size": roster_size,
            "history_count": len(history),
            "history": history,
        }

    # Fallback: query DB for this UUID
    try:
        from backend.models.corps import Corps
        from backend.models.show import Show
        from backend.models.agent_session import AgentSession, SessionStatus
        db = _get_db_session()
        try:
            corps = db.get(Corps, corps_id)
            if not corps:
                raise HTTPException(404, f"Corps '{corps_id}' not found")
            roster_size = db.query(AgentSession).filter(
                AgentSession.corps_id == corps_id,
                AgentSession.status == SessionStatus.ACTIVE
            ).count()

            # Find linked show
            show_info = None
            if corps.show_id:
                show = db.get(Show, corps.show_id)
                if show:
                    show_info = {
                        "show_id": show.id,
                        "title": show.title,
                        "status": show.status.value,
                        "description": show.description,
                    }
            # Also check if any show references this corps
            if not show_info:
                show = db.query(Show).filter(Show.corps_id == corps_id).first()
                if show:
                    show_info = {
                        "show_id": show.id,
                        "title": show.title,
                        "status": show.status.value,
                        "description": show.description,
                    }

            return {
                "corps_id": corps.id,
                "display_name": corps.name,
                "philosophy": "",
                "state": corps.status.value if corps.status else "unknown",
                "roster_size": roster_size,
                "history_count": 0,
                "history": [],
                "mascot": corps.mascot,
                "theme_id": corps.theme_id,
                "mode": corps.mode.value if corps.mode else None,
                "rehearsal_mode": corps.rehearsal_mode.value if corps.rehearsal_mode else None,
                "current_show": show_info,
            }
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(404, f"Corps '{corps_id}' not found")


# =========================================================================
# CORPS LIFECYCLE TRANSITIONS
# =========================================================================


@router.post("/corps/{corps_id}/ready-for-contest")
def v1_ready_for_contest(corps_id: str):
    """Transition a corps from ON_TOUR to READY_FOR_CONTEST."""
    _validate_id(corps_id, "corps_id")
    from backend.models.corps import Corps, CorpsStatus

    db = _get_db_session()
    try:
        corps = db.get(Corps, corps_id)
        if not corps:
            raise HTTPException(404, f"Corps '{corps_id}' not found")
        if corps.status != CorpsStatus.ON_TOUR:
            raise HTTPException(
                400,
                f"Corps must be ON_TOUR to become READY_FOR_CONTEST (current: {corps.status.value})",
            )
        corps.status = CorpsStatus.READY_FOR_CONTEST
        db.commit()
        return {
            "corps_id": corps.id,
            "display_name": corps.name,
            "state": corps.status.value,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to transition corps: {e}")
    finally:
        db.close()


@router.post("/corps/{corps_id}/return-to-tour")
def v1_return_to_tour(corps_id: str):
    """Return a corps from READY_FOR_CONTEST back to ON_TOUR for rework."""
    _validate_id(corps_id, "corps_id")
    from backend.models.corps import Corps, CorpsStatus

    db = _get_db_session()
    try:
        corps = db.get(Corps, corps_id)
        if not corps:
            raise HTTPException(404, f"Corps '{corps_id}' not found")
        if corps.status != CorpsStatus.READY_FOR_CONTEST:
            raise HTTPException(
                400,
                f"Corps must be READY_FOR_CONTEST to return to tour (current: {corps.status.value})",
            )
        corps.status = CorpsStatus.ON_TOUR
        db.commit()
        return {
            "corps_id": corps.id,
            "display_name": corps.name,
            "state": corps.status.value,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to transition corps: {e}")
    finally:
        db.close()


@router.post("/corps/{corps_id}/complete")
def v1_complete_corps(corps_id: str):
    """Complete a corps season — transition from READY_FOR_CONTEST to COMPLETED."""
    _validate_id(corps_id, "corps_id")
    from backend.models.corps import Corps, CorpsStatus, RehearsalMode
    from backend.models.segment import Segment, SegmentStatus
    from backend.models.rep import Rep
    from backend.models.agent_session import AgentSession

    db = _get_db_session()
    try:
        from backend.services.corps_service import complete_corps as complete_corps_service
        corps = complete_corps_service(db, corps_id)
        return {
            "corps_id": corps.id,
            "display_name": corps.name,
            "state": corps.status.value,
            "message": "Corps season completed successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to complete corps: {e}")
    finally:
        db.close()


# =========================================================================
# CORPS HISTORY & SEANCES
# =========================================================================


@router.get("/corps/{corps_id}/history")
def v1_get_corps_history(corps_id: str):
    """List past shows for a corps (builds/returns history index). Falls back to empty for DB-only corps."""
    _validate_id(corps_id, "corps_id")
    root = _get_root()
    from backend.services.corps_history import build_history_index
    try:
        index = build_history_index(root, corps_id)
        return index
    except FileNotFoundError:
        pass

    # Fallback: build history from filesystem scan for DB-only corps
    try:
        from backend.models.corps import Corps
        db = _get_db_session()
        try:
            corps = db.get(Corps, corps_id)
        finally:
            db.close()
        if not corps:
            raise HTTPException(404, f"Corps '{corps_id}' not found")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(404, f"Corps '{corps_id}' not found")

    # Scan seasons for performances/standings referencing this corps
    from backend.services.corps_history import _probe_artifacts, _discover_runs
    entries = []
    seasons_dir = root / "seasons"
    if seasons_dir.exists():
        for season_dir in sorted(seasons_dir.iterdir()):
            if not season_dir.is_dir():
                continue
            season_id = season_dir.name
            # Check if this corps has any presence in this season
            perf_dir = season_dir / "performances" / corps_id
            standings_path = season_dir / "standings.yaml"
            has_perf = perf_dir.is_dir()
            has_standing = False
            placement = 0
            final_score = 0.0
            show_slug = None

            # Check standings for this corps
            if standings_path.exists():
                try:
                    standings = safe_load_yaml_dict(standings_path.read_text())
                    for result in standings.get("results", []):
                        if result.get("corps_id") == corps_id:
                            has_standing = True
                            placement = result.get("rank", 0)
                            final_score = result.get("final_score", 0.0)
                            break
                except Exception:
                    pass

            # Check scores.yaml for show_slug
            scores_path = perf_dir / "scores.yaml" if has_perf else None
            if scores_path and scores_path.exists():
                try:
                    scores = safe_load_yaml_dict(scores_path.read_text())
                    show_slug = scores.get("show_slug")
                except Exception:
                    pass

            # Discover show_slug from run manifests if not in scores
            if not show_slug and has_perf:
                runs = _discover_runs(root, corps_id, season_id)
                for run_id in runs:
                    manifest_path = season_dir / "performances" / corps_id / run_id / "manifest.yaml"
                    if manifest_path.exists():
                        try:
                            m = safe_load_yaml_dict(manifest_path.read_text())
                            if m.get("show_slug"):
                                show_slug = m["show_slug"]
                                break
                        except Exception:
                            pass

            if has_perf or has_standing:
                entry_id = f"{corps_id}-{season_id}"
                artifacts = _probe_artifacts(root, corps_id, season_id, show_slug)
                runs = _discover_runs(root, corps_id, season_id)
                entries.append({
                    "entry_id": entry_id,
                    "season_id": season_id,
                    "show_slug": show_slug,
                    "placement": placement,
                    "final_score": final_score,
                    "artifacts": artifacts,
                    "runs": runs,
                })

    entries.sort(key=lambda e: e["entry_id"])
    return {
        "corps_id": corps_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
    }


@router.get("/corps/{corps_id}/seances")
def v1_list_corps_seances(corps_id: str):
    """List seance sessions for a corps by scanning seances/ directory."""
    _validate_id(corps_id, "corps_id")
    root = _get_root()
    seances_dir = root / "seances"
    if not seances_dir.exists():
        return []
    results = []
    for sdir in seances_dir.iterdir():
        if not sdir.is_dir():
            continue
        session_path = sdir / "session.yaml"
        if not session_path.is_file():
            continue
        try:
            data = safe_load_yaml_dict(session_path.read_text())
            if isinstance(data, dict) and data.get("corps_id") == corps_id:
                results.append({
                    "seance_id": data.get("seance_id", sdir.name),
                    "corps_id": data.get("corps_id"),
                    "entry_id": data.get("entry_id", ""),
                    "season_id": data.get("season_id", ""),
                    "show_slug": data.get("show_slug"),
                    "participant": data.get("participant", "user"),
                    "created_at": data.get("created_at", ""),
                    "status": data.get("status", "active"),
                    "context_binder": data.get("context_binder", []),
                })
        except Exception:
            continue
    results.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return results


# =========================================================================
# CRITIQUE
# =========================================================================


@router.post("/corps/{corps_id}/critique/{round_num}/clarify")
def v1_clarify_critique(corps_id: str, round_num: int, req: CritiqueClarifyRequest):
    """Clarify judge critique for a corps and round."""
    _validate_id(corps_id, "corps_id")
    root = _get_root()
    critique_path = _find_critique_file(root, corps_id, round_num)
    if not critique_path:
        raise HTTPException(404, "Critique round not found")

    critique_text = critique_path.read_text()

    from backend.api.app import get_task_manager
    tm = get_task_manager()
    llm_client = tm.llm_client if tm else None

    if not llm_client:
        return {"answer": "LLM unavailable", "critique_path": str(critique_path)}

    from backend.services.llm_client import LLMMessage
    from backend.models.agent_definition import ModelTier

    context = critique_text[:6000]
    messages = [
        LLMMessage(role="system", content="You are a DCI judge clarifying feedback from a critique report. Answer concisely and stay grounded in the report."),
        LLMMessage(role="user", content=f"Critique report:\n{context}\n\nQuestion: {req.question}\nAnswer with actionable clarification."),
    ]
    resp = llm_client.chat(messages, model_tier=ModelTier.HAIKU)
    return {"answer": resp.content.strip(), "critique_path": str(critique_path)}


# =========================================================================
# FEEDBACK & ED CHAT
# =========================================================================


@router.post("/corps/{corps_id}/feedback")
def v1_send_corps_feedback(corps_id: str, req: CorpsFeedbackRequest):
    """Deliver user feedback as directive to corps ED via auto-completing critique session."""
    _validate_id(corps_id, "corps_id")
    from backend.services.critique_service import start_critique, complete_critique
    from backend.api.app import get_task_manager
    tm = get_task_manager()
    llm_client = tm.llm_client if tm else None

    db = _get_db_session()
    try:
        from backend.models.corps import Corps
        corps = db.get(Corps, corps_id)
        if not corps:
            raise HTTPException(404, "Corps not found")

        # Create a critique session with user feedback as the opening message
        session = start_critique(
            db, competition_id=f"feedback-{corps_id}",
            corps_id=corps_id, judge_type="user_feedback",
            llm_client=None,  # No LLM for opening — we use the user's feedback directly
        )
        # Replace the auto-generated opening with the user's feedback
        session.conversation = [{"role": "judge", "content": req.feedback}]
        db.commit()

        # Auto-complete to extract action items
        completed = complete_critique(db, session.id, llm_client=llm_client)
        return {"status": "delivered", "session_id": completed.id}
    finally:
        db.close()


@router.post("/corps/{corps_id}/ed-chat")
def v1_start_ed_chat(corps_id: str):
    """Start a multi-turn chat with the corps Executive Director."""
    _validate_id(corps_id, "corps_id")
    from backend.services.critique_service import start_critique
    from backend.api.app import get_task_manager
    tm = get_task_manager()
    llm_client = tm.llm_client if tm else None

    db = _get_db_session()
    try:
        from backend.models.corps import Corps
        corps = db.get(Corps, corps_id)
        if not corps:
            raise HTTPException(404, "Corps not found")

        session = start_critique(
            db, competition_id=f"ed-chat-{corps_id}",
            corps_id=corps_id, judge_type="user",
            llm_client=llm_client,
        )
        # Override staff_role to executive_director
        session.staff_role = "executive_director"
        db.commit()
        db.refresh(session)

        return {
            "id": session.id,
            "competition_id": session.competition_id,
            "corps_id": session.corps_id,
            "judge_type": session.judge_type,
            "staff_role": session.staff_role,
            "status": session.status.value,
            "conversation": session.conversation,
            "action_items": session.action_items,
            "created_at": str(session.created_at),
        }
    finally:
        db.close()


@router.get("/corps/{corps_id}/adaptation-history")
def v1_get_adaptation_history(corps_id: str):
    """View agent adaptation attempts and outcomes for a corps."""
    _validate_id(corps_id, "corps_id")
    from backend.services.agent_adaptation import get_adaptation_history
    db = _get_db_session()
    try:
        return get_adaptation_history(db, corps_id)
    finally:
        db.close()


# =========================================================================
# CHAT & SCORESHEET
# =========================================================================


@router.get("/corps/{corps_id}/chat")
def v1_get_chat_history(corps_id: str, limit: int = 100):
    """Get chat message history for a corps."""
    _validate_id(corps_id, "corps_id")
    from backend.models.message import Message

    db = _get_db_session()
    try:
        messages = (
            db.query(Message)
            .filter(Message.corps_id == corps_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .all()
        )
        return [{
            "id": m.id,
            "type": m.type.value if m.type else "directive",
            "from_role": m.from_role,
            "to_role": m.to_role,
            "subject": m.subject,
            "body": m.body,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        } for m in reversed(messages)]
    finally:
        db.close()


@router.post("/corps/{corps_id}/chat")
def v1_send_chat(corps_id: str, data: dict):
    """Send a chat message to a corps agent."""
    _validate_id(corps_id, "corps_id")
    from backend.api.app import get_task_manager

    content = data.get("content", "")
    to_role = data.get("to_role", "executive_director")
    if not content:
        raise HTTPException(400, "content is required")

    tm = get_task_manager()
    if not tm:
        raise HTTPException(503, "Task manager not available")

    db = _get_db_session()
    try:
        # Record user message
        from backend.models.message import Message, MessageType
        msg = Message(
            corps_id=corps_id,
            type=MessageType.DIRECTIVE,
            from_role="user",
            to_role=to_role,
            subject="User chat",
            body=content,
        )
        db.add(msg)
        db.commit()

        # Find and trigger the target agent
        session_id = tm.get_session_for_role(db, corps_id, to_role)
        if session_id:
            tm.start_agent(
                session_id=session_id,
                task_description=f"Respond to user message: {content[:200]}",
            )

        return {
            "id": msg.id,
            "status": "sent",
            "to_role": to_role,
        }
    finally:
        db.close()


@router.get("/corps/{corps_id}/scoresheet")
def v1_get_scoresheet(corps_id: str):
    """Get latest scoresheet for a corps."""
    _validate_id(corps_id, "corps_id")
    try:
        from backend.models.scoresheet import Scoresheet
    except ImportError:
        import logging
        logging.getLogger(__name__).debug("Scoresheet model not available, returning empty scoresheet for %s", corps_id)
        return {"corps_id": corps_id, "scores": {}, "total": 0}

    db = _get_db_session()
    try:
        scoresheet = (
            db.query(Scoresheet)
            .filter(Scoresheet.corps_id == corps_id)
            .order_by(Scoresheet.created_at.desc())
            .first()
        )
        if not scoresheet:
            return {"corps_id": corps_id, "scores": {}, "total": 0}
        return {
            "corps_id": corps_id,
            "id": scoresheet.id,
            "scores": scoresheet.scores if isinstance(scoresheet.scores, dict) else {},
            "total": scoresheet.total_score or 0,
            "created_at": scoresheet.created_at.isoformat() if scoresheet.created_at else None,
        }
    finally:
        db.close()


# =========================================================================
# ROSTER
# =========================================================================


@router.get("/corps/{corps_id}/roster")
def v1_corps_roster(corps_id: str):
    """Get agent roster for a corps with performer data."""
    _validate_id(corps_id, "corps_id")
    from backend.models.agent_session import AgentSession
    from backend.models.agent_definition import AgentDefinition, ROLE_CLASSIFICATIONS, AgentClassification
    from backend.models.performer import Performer
    from datetime import datetime, timezone

    db = _get_db_session()
    try:
        sessions = (
            db.query(AgentSession)
            .filter(AgentSession.corps_id == corps_id)
            .all()
        )
        results = []
        for s in sessions:
            defn = db.get(AgentDefinition, s.definition_id) if s.definition_id else None
            performer = db.get(Performer, s.performer_id) if s.performer_id else None
            role = defn.role if defn else "unknown"

            # Classify into staff group
            classification = ROLE_CLASSIFICATIONS.get(role)
            if classification == AgentClassification.ADMINISTRATIVE:
                group = "Administrative Staff"
            elif classification == AgentClassification.INSTRUCTIONAL:
                group = "Instructional Staff"
            elif classification == AgentClassification.PERFORMING:
                group = "Performing Members"
            else:
                group = "Other"

            # Calculate tenure
            tenure_days = None
            if s.started_at:
                tenure_days = (datetime.now(timezone.utc) - s.started_at).days

            results.append({
                "session_id": s.id,
                "definition_id": s.definition_id,
                "role": role,
                "nickname": defn.nickname if defn else None,
                "model_tier": defn.model_tier.value if defn else "unknown",
                "status": s.status.value,
                "group": group,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "tenure_days": tenure_days,
                "performer_id": s.performer_id,
                "performer_name": performer.name if performer else None,
                "performer_trust_score": performer.trust_score if performer else None,
                "performer_status": performer.status.value if performer else None,
                "performer_total_sessions": performer.total_sessions if performer else None,
                "performer_successful_sessions": performer.successful_sessions if performer else None,
            })

        # Sort: Administrative > Instructional > Performing, then by role name
        group_order = {"Administrative Staff": 0, "Instructional Staff": 1, "Performing Members": 2, "Other": 3}
        results.sort(key=lambda r: (group_order.get(r["group"], 99), r["role"]))
        return results
    finally:
        db.close()


@router.post("/corps/{corps_id}/roster/hire")
def v1_corps_hire(corps_id: str, data: dict):
    """Hire a performer from the talent pool into this corps."""
    _validate_id(corps_id, "corps_id")
    performer_id = data.get("performer_id")
    role = data.get("role")
    if not performer_id or not role:
        raise HTTPException(400, "performer_id and role are required")

    from backend.models.performer import Performer, PerformerStatus
    from backend.models.agent_session import AgentSession
    from backend.models.agent_definition import AgentDefinition

    db = _get_db_session()
    try:
        performer = db.get(Performer, performer_id)
        if not performer:
            raise HTTPException(404, f"Performer '{performer_id}' not found")
        if performer.status != PerformerStatus.ACTIVE:
            raise HTTPException(400, f"Performer is {performer.status.value}, cannot hire")

        # Find an unassigned session for this role in the corps
        session = (
            db.query(AgentSession)
            .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
            .filter(
                AgentSession.corps_id == corps_id,
                AgentDefinition.role == role,
                AgentSession.performer_id.is_(None),
            )
            .first()
        )
        if not session:
            raise HTTPException(400, f"No open slot for role '{role}' in this corps")

        session.performer_id = performer.id
        db.commit()
        return {"status": "hired", "performer_id": performer.id, "session_id": session.id, "role": role}
    finally:
        db.close()


@router.post("/corps/{corps_id}/roster/dismiss")
def v1_corps_dismiss(corps_id: str, data: dict):
    """Dismiss a performer back to the talent pool."""
    _validate_id(corps_id, "corps_id")
    session_id = data.get("session_id")
    if not session_id:
        raise HTTPException(400, "session_id is required")

    from backend.models.agent_session import AgentSession

    db = _get_db_session()
    try:
        session = db.get(AgentSession, session_id)
        if not session or session.corps_id != corps_id:
            raise HTTPException(404, "Session not found in this corps")
        if not session.performer_id:
            raise HTTPException(400, "No performer assigned to this session")

        performer_id = session.performer_id
        session.performer_id = None
        db.commit()
        return {"status": "dismissed", "performer_id": performer_id, "session_id": session_id}
    finally:
        db.close()


@router.post("/corps/{corps_id}/roster/fire")
def v1_corps_fire(corps_id: str, data: dict):
    """Fire a staff member — releases performer back to marketplace with reduced trust."""
    _validate_id(corps_id, "corps_id")
    session_id = data.get("session_id")
    if not session_id:
        raise HTTPException(400, "session_id is required")

    from backend.models.agent_session import AgentSession
    from backend.models.performer import Performer

    db = _get_db_session()
    try:
        session = db.get(AgentSession, session_id)
        if not session or session.corps_id != corps_id:
            raise HTTPException(404, "Session not found in this corps")
        if not session.performer_id:
            raise HTTPException(400, "No performer assigned to this session")

        performer = db.get(Performer, session.performer_id)
        performer_id = session.performer_id
        session.performer_id = None
        if performer:
            performer.trust_score = max(0, performer.trust_score - 10.0)
        db.commit()
        return {"status": "fired", "performer_id": performer_id, "session_id": session_id}
    finally:
        db.close()


# =========================================================================
# MODE SWITCHING
# =========================================================================


@router.put("/corps/{corps_id}/mode")
def v1_switch_corps_mode(corps_id: str, data: dict):
    """Switch corps operational mode."""
    _validate_id(corps_id, "corps_id")
    from backend.models.corps import Corps, CorpsMode

    mode_str = data.get("mode", "")
    try:
        new_mode = CorpsMode(mode_str)
    except ValueError:
        valid = [m.value for m in CorpsMode]
        raise HTTPException(400, f"Invalid mode '{mode_str}'. Valid: {valid}")

    db = _get_db_session()
    try:
        corps = db.get(Corps, corps_id)
        if not corps:
            raise HTTPException(404, f"Corps '{corps_id}' not found")
        corps.mode = new_mode
        db.commit()
        return {"corps_id": corps_id, "mode": new_mode.value}
    finally:
        db.close()


@router.post("/corps/{corps_id}/mode")
async def v1_switch_corps_mode_async(corps_id: str, data: CorpsModeSwitchRequest):
    """Switch a corps to a new operational mode."""
    from backend.models.corps import CorpsMode
    from backend.services.mode_manager import switch_mode, ModeError
    from backend.api.app import manager

    db = _get_db_session()
    try:
        new_mode = CorpsMode(data.mode)
        corps = switch_mode(db, corps_id, new_mode)
        await manager.broadcast(corps_id, {
            "type": "mode_switch", "corps_id": corps_id, "mode": new_mode.value,
        })
        return {"id": corps.id, "mode": corps.mode.value}
    except ValueError:
        raise HTTPException(400, f"Invalid mode: {data.mode}")
    except ModeError as e:
        raise HTTPException(400, str(e))
    finally:
        db.close()


# =========================================================================
# THEME
# =========================================================================


@router.get("/corps/{corps_id}/theme")
def v1_get_corps_theme(corps_id: str):
    from backend.models.corps import Corps
    db = _get_db_session()
    try:
        corps = db.get(Corps, corps_id)
        if not corps:
            raise HTTPException(404, "Corps not found")
        return {"corps_id": corps.id, "theme_id": corps.theme_id,
                "mascot": corps.mascot, "uniform_concept": corps.uniform_concept}
    finally:
        db.close()


@router.put("/corps/{corps_id}/theme")
def v1_update_corps_theme(corps_id: str, data: CorpsThemeUpdateRequest):
    from backend.services.corps_service import update_corps_theme, CorpsError
    db = _get_db_session()
    try:
        corps = update_corps_theme(db, corps_id, theme_id=data.theme_id,
                                   mascot=data.mascot, uniform_concept=data.uniform_concept)
        return {"corps_id": corps.id, "theme_id": corps.theme_id,
                "mascot": corps.mascot, "uniform_concept": corps.uniform_concept}
    except CorpsError as e:
        raise HTTPException(404, str(e))
    finally:
        db.close()


# =========================================================================
# PROGRESSION & REHEARSAL
# =========================================================================


@router.get("/corps/{corps_id}/progression")
def v1_get_progression(corps_id: str):
    """Current rehearsal mode, milestones, and what's needed to advance."""
    from backend.models.corps import Corps, RehearsalMode
    from backend.services.rehearsal_progression import (
        _basics_met, _sectionals_met, _full_ensemble_met, _next_mode,
    )
    db = _get_db_session()
    try:
        corps = db.get(Corps, corps_id)
        if not corps:
            raise HTTPException(404, "Corps not found")
        current = corps.rehearsal_mode
        checks = {
            RehearsalMode.BASICS: ("basics_met", _basics_met),
            RehearsalMode.SECTIONALS: ("sectionals_met", _sectionals_met),
            RehearsalMode.FULL_ENSEMBLE: ("full_ensemble_met", _full_ensemble_met),
        }
        milestones = {}
        for mode, (key, fn) in checks.items():
            milestones[key] = fn(db, corps_id)
        return {
            "corps_id": corps_id,
            "status": corps.status.value,
            "current_mode": current.value if current else None,
            "next_mode": _next_mode(current).value if current and _next_mode(current) else None,
            "milestones": milestones,
        }
    finally:
        db.close()


@router.post("/corps/{corps_id}/rehearsal-mode")
def v1_set_rehearsal_mode(corps_id: str, data: RehearsalModeSetRequest):
    from backend.models.corps import RehearsalMode
    from backend.services.corps_service import set_rehearsal_mode, CorpsError
    db = _get_db_session()
    try:
        mode = RehearsalMode(data.mode)
        corps = set_rehearsal_mode(db, corps_id, mode)
        return {"id": corps.id, "rehearsal_mode": corps.rehearsal_mode.value}
    except (ValueError, CorpsError) as e:
        raise HTTPException(400, str(e))
    finally:
        db.close()


# =========================================================================
# METRICS, EVALUATE, SEASON TRANSITION, AGEOUTS, MERGE CHECK
# =========================================================================


@router.get("/corps/{corps_id}/metrics")
def v1_corps_metrics(corps_id: str):
    """Get aggregate metrics for a corps."""
    from backend.services.metrics_collector import collect_corps_metrics
    import dataclasses
    db = _get_db_session()
    try:
        metrics = collect_corps_metrics(db, corps_id)
        return dataclasses.asdict(metrics)
    finally:
        db.close()


@router.post("/corps/{corps_id}/evaluate")
def v1_evaluate_corps(corps_id: str):
    """Run post-show evaluation on all performers in a corps."""
    from backend.services.evaluation_service import evaluate_corps
    db = _get_db_session()
    try:
        return evaluate_corps(db, corps_id)
    finally:
        db.close()


@router.post("/corps/{corps_id}/season-transition")
def v1_season_transition(corps_id: str):
    """Run end-of-season lifecycle: age performers, check ageouts."""
    from backend.services.lifecycle_manager import conduct_season_transition
    db = _get_db_session()
    try:
        return conduct_season_transition(db, corps_id)
    finally:
        db.close()


@router.get("/corps/{corps_id}/ageouts")
def v1_get_ageouts(corps_id: str):
    """Get performers approaching ageout for this corps."""
    from backend.services.lifecycle_manager import check_ageouts
    db = _get_db_session()
    try:
        ageouts = check_ageouts(db)
        return [{"id": p.id, "name": p.name, "age": p.age, "role_type": p.role_type} for p in ageouts]
    finally:
        db.close()


@router.post("/corps/{corps_id}/merge-check")
def v1_merge_check(corps_id: str):
    from backend.services.corps_service import merge_monitor_check
    db = _get_db_session()
    try:
        result = merge_monitor_check(db, corps_id)
        return {
            "checked": result.checked,
            "merged": result.merged,
            "conflicts": result.conflicts,
            "merged_segment_ids": result.merged_segment_ids,
            "conflict_segment_ids": result.conflict_segment_ids,
        }
    finally:
        db.close()


# =========================================================================
# METRONOME
# =========================================================================


@router.post("/corps/{corps_id}/metronome/tick")
def v1_metronome_tick(corps_id: str):
    """Manual metronome tick for a corps."""
    _validate_id(corps_id, "corps_id")
    from backend.tools.metronome import tick

    db = _get_db_session()
    try:
        result = tick(db, corps_id)
        return {
            "checked": result.checked,
            "reclaimed": result.reclaimed,
            "reclaimed_rep_ids": result.reclaimed_rep_ids,
        }
    finally:
        db.close()


# =========================================================================
# WORK LOG
# =========================================================================


@router.get("/corps/{corps_id}/work-log")
def v1_corps_work_log(corps_id: str, limit: int = 100, event_type: Optional[str] = None):
    """Get structured work log for a corps."""
    _validate_id(corps_id, "corps_id")
    from backend.models.work_log import WorkLog
    from backend.models.agent_session import AgentSession
    from backend.models.agent_definition import AgentDefinition

    db = _get_db_session()
    try:
        query = db.query(WorkLog).filter(WorkLog.corps_id == corps_id)
        if event_type:
            query = query.filter(WorkLog.event_type == event_type)
        logs = query.order_by(WorkLog.timestamp.desc()).limit(limit).all()

        session_ids = {log.session_id for log in logs if log.session_id}
        nicknames = {}
        if session_ids:
            sessions = db.query(AgentSession).filter(AgentSession.id.in_(session_ids)).all()
            defn_ids = {s.definition_id for s in sessions if s.definition_id}
            defns = {d.id: d for d in db.query(AgentDefinition).filter(AgentDefinition.id.in_(defn_ids)).all()} if defn_ids else {}
            for s in sessions:
                defn = defns.get(s.definition_id)
                if defn and defn.nickname:
                    nicknames[s.id] = defn.nickname

        return [{
            "id": log.id,
            "session_id": log.session_id,
            "corps_id": log.corps_id,
            "role": log.role,
            "nickname": nicknames.get(log.session_id),
            "event_type": log.event_type,
            "phase": log.phase,
            "details": log.details,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        } for log in logs]
    finally:
        db.close()


@router.get("/corps/{corps_id}/work-log/analysis")
def v1_work_log_analysis(corps_id: str):
    """Aggregate work log analysis: event distribution, tool usage, failure patterns."""
    _validate_id(corps_id, "corps_id")
    from backend.models.work_log import WorkLog
    from sqlalchemy import func

    db = _get_db_session()
    try:
        # Event type distribution
        event_counts = (
            db.query(WorkLog.event_type, func.count(WorkLog.id))
            .filter(WorkLog.corps_id == corps_id)
            .group_by(WorkLog.event_type)
            .all()
        )

        # Tool usage counts (from details JSON containing "tool" key)
        tool_logs = (
            db.query(WorkLog.details)
            .filter(WorkLog.corps_id == corps_id, WorkLog.event_type.in_(["tool_call", "tool_success", "tool_error"]))
            .all()
        )
        tool_usage: dict[str, dict] = {}
        for (details_str,) in tool_logs:
            if not details_str:
                continue
            try:
                details = json.loads(details_str) if details_str.startswith("{") else {}
            except (json.JSONDecodeError, TypeError):
                details = {}
            tool_name = details.get("tool", "unknown")
            if tool_name not in tool_usage:
                tool_usage[tool_name] = {"calls": 0, "successes": 0, "errors": 0}
            tool_usage[tool_name]["calls"] += 1
            if details.get("success"):
                tool_usage[tool_name]["successes"] += 1
            elif details.get("success") is False:
                tool_usage[tool_name]["errors"] += 1

        # Failure patterns (error details)
        failures = (
            db.query(WorkLog.role, WorkLog.details)
            .filter(WorkLog.corps_id == corps_id, WorkLog.event_type.in_(["agent_fail", "tool_error"]))
            .order_by(WorkLog.timestamp.desc())
            .limit(20)
            .all()
        )
        failure_details = []
        for role, details_str in failures:
            try:
                details = json.loads(details_str) if details_str and details_str.startswith("{") else {}
            except (json.JSONDecodeError, TypeError):
                details = {}
            failure_details.append({"role": role, "error": details.get("error", str(details_str)[:200])})

        # Total count
        total = db.query(func.count(WorkLog.id)).filter(WorkLog.corps_id == corps_id).scalar()

        return {
            "corps_id": corps_id,
            "total_events": total,
            "event_distribution": {et: count for et, count in event_counts},
            "tool_usage": tool_usage,
            "recent_failures": failure_details,
            "failure_rate": (
                sum(1 for f in failure_details) / max(total, 1) * 100
            ),
        }
    finally:
        db.close()


# =========================================================================
# MESSAGES: POLLING & SEND
# =========================================================================


@router.get("/corps/{corps_id}/messages/poll")
def v1_poll_messages(corps_id: str, since: str = None):
    """Poll for new messages since a timestamp."""
    from backend.models.message import Message
    db = _get_db_session()
    try:
        q = db.query(Message).filter(Message.corps_id == corps_id)
        if since:
            from datetime import datetime
            q = q.filter(Message.created_at > datetime.fromisoformat(since))
        messages = q.order_by(Message.created_at.asc()).limit(100).all()
        return [{
            "id": m.id,
            "from_role": m.from_role,
            "to_role": m.to_role,
            "subject": m.subject,
            "body": m.body,
            "type": m.type.value if m.type else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        } for m in messages]
    finally:
        db.close()


@router.post("/corps/{corps_id}/messages")
def v1_send_message(corps_id: str, data: MessageCreateV1Request):
    from backend.models.message import MessageType, MessagePriority
    from backend.services.message_service import send_message, InvalidMessagePath, InvalidMessageType
    db = _get_db_session()
    try:
        msg = send_message(
            db, corps_id=corps_id, from_role=data.from_role,
            type=MessageType(data.type), subject=data.subject, body=data.body,
            to_role=data.to_role, priority=MessagePriority(data.priority),
            segment_id=data.segment_id,
        )
        return {"id": msg.id, "type": msg.type.value, "subject": msg.subject}
    except (ValueError, InvalidMessagePath, InvalidMessageType) as e:
        raise HTTPException(400, str(e))
    finally:
        db.close()


# =========================================================================
# CORPS COMMANDS
# =========================================================================


@router.get("/corps-commands")
def v1_list_corps_commands():
    """List all available corps commands."""
    return CORPS_COMMANDS


@router.post("/corps/{corps_id}/command")
async def v1_execute_corps_command(corps_id: str, data: CorpsCommandRequest):
    """Execute a corps command."""
    from backend.models.corps import Corps, CorpsStatus, RehearsalMode
    from backend.services.corps_service import (
        go_on_tour, return_to_camps, set_rehearsal_mode, disband_corps, merge_monitor_check, CorpsError,
    )
    from backend.tools.metronome import tick
    from backend.api.app import get_task_manager, manager

    db = _get_db_session()
    try:
        corps = db.get(Corps, corps_id)
        if not corps:
            raise HTTPException(404, "Corps not found")

        cmd = data.command
        if cmd not in CORPS_COMMANDS:
            raise HTTPException(400, f"Unknown command: {cmd}")

        result = {"command": cmd, "corps_id": corps_id, "status": "ok", "detail": ""}
        tm = get_task_manager()

        if cmd == "resume_hut":
            if tm:
                from backend.models.agent_session import AgentSession, SessionStatus
                from backend.models.agent_definition import AgentDefinition
                unique_roles = (
                    db.query(AgentDefinition.role)
                    .join(AgentSession)
                    .filter(AgentSession.corps_id == corps_id)
                    .distinct()
                    .all()
                )
                woken = 0
                for (role,) in unique_roles:
                    sid = tm.get_session_for_role(db, corps_id, role)
                    if sid and not tm.is_active(sid):
                        tm.start_agent(
                            session_id=sid,
                            task_description=(
                                f"RESUME HUT! The corps has been called to attention and work is resuming. "
                                f"Check your current assignments and continue working. Corps ID: {corps_id}"
                            ),
                            corps_id=corps_id,
                        )
                        woken += 1
                result["detail"] = f"Woke {woken} agents"
            await manager.broadcast(corps_id, {
                "type": "command", "command": "resume_hut",
                "content": "Resume, Hut! All agents resuming work.",
            })

        elif cmd == "attention":
            if tm:
                ed_session = tm.get_session_for_role(db, corps_id, "executive_director")
                if ed_session and not tm.is_active(ed_session):
                    tm.start_agent(
                        session_id=ed_session,
                        task_description=(
                            f"ATTENTION! The director has called the corps to attention. "
                            f"Report the current status of all work in progress. Corps ID: {corps_id}. "
                            f"Check all segments and reps, then provide a full status report."
                        ),
                        corps_id=corps_id,
                    )
            await manager.broadcast(corps_id, {
                "type": "command", "command": "attention",
                "content": "Attention! Status report requested.",
            })
            result["detail"] = "Status report requested from ED"

        elif cmd == "at_ease":
            corps.status = CorpsStatus.WINTER_CAMPS
            db.commit()
            await manager.broadcast(corps_id, {
                "type": "command", "command": "at_ease",
                "content": "At ease. Returning to Winter Camps. Finishing current tasks, then standing by.",
            })
            result["detail"] = "Corps returned to Winter Camps"

        elif cmd == "dismissed":
            try:
                disband_corps(db, corps_id)
                await manager.broadcast(corps_id, {
                    "type": "command", "command": "dismissed",
                    "content": "Corps dismissed. All agents standing down.",
                })
                result["detail"] = "Corps disbanded"
            except CorpsError as e:
                raise HTTPException(400, str(e))

        elif cmd in ("basics", "sectionals", "full_ensemble", "run_through"):
            try:
                mode = RehearsalMode(cmd)
                set_rehearsal_mode(db, corps_id, mode)
                await manager.broadcast(corps_id, {
                    "type": "command", "command": cmd,
                    "content": f"Rehearsal mode set to: {cmd.replace('_', ' ')}",
                })
                result["detail"] = f"Rehearsal mode: {cmd}"
            except (ValueError, CorpsError) as e:
                raise HTTPException(400, str(e))

        elif cmd == "go_on_tour":
            try:
                go_on_tour(db, corps_id)
                await manager.broadcast(corps_id, {
                    "type": "command", "command": "go_on_tour",
                    "content": "On Tour — autonomous execution active.",
                })
                result["detail"] = "On Tour"
            except CorpsError as e:
                raise HTTPException(400, str(e))

        elif cmd == "return_to_camps":
            try:
                return_to_camps(db, corps_id)
                await manager.broadcast(corps_id, {
                    "type": "command", "command": "return_to_camps",
                    "content": "Returned to Winter Camps — planning phase.",
                })
                result["detail"] = "Returned to Winter Camps"
            except CorpsError as e:
                raise HTTPException(400, str(e))

        elif cmd == "metronome_tick":
            tick_result = tick(db, corps_id)
            await manager.broadcast(corps_id, {
                "type": "metronome_tick", "corps_id": corps_id,
                "checked": tick_result.checked, "reclaimed": tick_result.reclaimed,
            })
            result["detail"] = f"Checked {tick_result.checked}, reclaimed {tick_result.reclaimed}"

        elif cmd == "merge_check":
            merge_result = merge_monitor_check(db, corps_id)
            await manager.broadcast(corps_id, {
                "type": "merge_check", "corps_id": corps_id,
                "merged": merge_result.merged, "conflicts": merge_result.conflicts,
            })
            result["detail"] = f"Merged {merge_result.merged}, conflicts {merge_result.conflicts}"

        return result
    finally:
        db.close()


# =========================================================================
# BASICS & BANQUET (Improvement)
# =========================================================================


@router.post("/corps/{corps_id}/basics/{caption}")
def v1_run_basics(corps_id: str, caption: str):
    """Run basics drill for a caption section."""
    from backend.services.improvement import run_basics
    db = _get_db_session()
    try:
        result = run_basics(db, corps_id, caption)
        return result
    finally:
        db.close()


@router.get("/corps/{corps_id}/banquet")
def v1_get_banquet(corps_id: str):
    """Get banquet/awards data for a corps."""
    from backend.models.reputation import Reputation
    db = _get_db_session()
    try:
        reps = (
            db.query(Reputation)
            .filter(Reputation.corps_id == corps_id)
            .order_by(Reputation.score.desc())
            .limit(50)
            .all()
        )
        return [{
            "id": r.id,
            "agent_id": r.agent_id,
            "score": r.score,
            "dimension": r.dimension,
            "critique": r.critique,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in reps]
    finally:
        db.close()


# =========================================================================
# STAFF MARKETPLACE (corps-scoped)
# =========================================================================


@router.post("/corps/{corps_id}/staff/hire")
def v1_hire_staff(corps_id: str, req: HireStaffRequest):
    """Hire a performer to a corps by creating an agent definition and session."""
    from backend.models.performer import Performer
    from backend.models.agent_definition import AgentDefinition
    from backend.models.agent_session import AgentSession, SessionStatus

    _validate_id(corps_id, "corps_id")
    _validate_id(req.performer_id, "performer_id")

    db = _get_db_session()
    try:
        performer = db.query(Performer).filter(Performer.id == req.performer_id).first()
        if not performer:
            raise HTTPException(404, f"Performer {req.performer_id} not found")

        # Create an AgentDefinition for this role in the corps
        agent_def = AgentDefinition(
            id=str(uuid.uuid4()),
            corps_id=corps_id,
            role=req.role,
            performer_id=req.performer_id,
        )
        db.add(agent_def)

        # Spawn an active AgentSession linked to the performer
        session = AgentSession(
            id=str(uuid.uuid4()),
            agent_definition_id=agent_def.id,
            performer_id=req.performer_id,
            corps_id=corps_id,
            status=SessionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc),
        )
        db.add(session)
        db.commit()

        return {
            "agent_definition_id": agent_def.id,
            "session_id": session.id,
            "corps_id": corps_id,
            "performer_id": req.performer_id,
            "role": req.role,
            "status": session.status.value,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to hire staff: {e}")
    finally:
        db.close()


@router.post("/corps/{corps_id}/staff/release")
def v1_release_staff(corps_id: str, req: ReleaseStaffRequest):
    """Release a performer from a corps, ending their active session."""
    from backend.models.performer import Performer
    from backend.models.agent_session import AgentSession, SessionStatus

    _validate_id(corps_id, "corps_id")
    _validate_id(req.performer_id, "performer_id")

    db = _get_db_session()
    try:
        # Find the active session for this performer in this corps
        session = (
            db.query(AgentSession)
            .filter(
                AgentSession.performer_id == req.performer_id,
                AgentSession.corps_id == corps_id,
                AgentSession.status == SessionStatus.ACTIVE,
            )
            .first()
        )
        if not session:
            raise HTTPException(
                404,
                f"No active session for performer {req.performer_id} in corps {corps_id}",
            )

        session.status = SessionStatus.COMPLETED
        session.ended_at = datetime.now(timezone.utc)

        # Apply optional trust penalty
        if req.trust_penalty:
            performer = db.query(Performer).filter(Performer.id == req.performer_id).first()
            if performer and performer.trust_score is not None:
                performer.trust_score = max(0.0, performer.trust_score - req.trust_penalty)

        db.commit()

        return {
            "session_id": session.id,
            "corps_id": corps_id,
            "performer_id": req.performer_id,
            "status": session.status.value,
            "completed_at": session.ended_at.isoformat(),
            "trust_penalty_applied": req.trust_penalty,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to release staff: {e}")
    finally:
        db.close()


@router.get("/corps/{corps_id}/staff")
def v1_list_corps_staff(corps_id: str):
    """List current active staff for a corps."""
    from backend.models.performer import Performer
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.agent_definition import AgentDefinition

    _validate_id(corps_id, "corps_id")

    db = _get_db_session()
    try:
        results = (
            db.query(AgentSession, Performer, AgentDefinition)
            .join(Performer, AgentSession.performer_id == Performer.id)
            .join(AgentDefinition, AgentSession.agent_definition_id == AgentDefinition.id)
            .filter(
                AgentSession.corps_id == corps_id,
                AgentSession.status == SessionStatus.ACTIVE,
            )
            .all()
        )

        return {
            "corps_id": corps_id,
            "staff": [
                {
                    "session_id": session.id,
                    "performer_id": performer.id,
                    "performer_name": performer.name,
                    "role": agent_def.role,
                    "trust_score": performer.trust_score,
                    "started_at": session.started_at.isoformat() if session.started_at else None,
                    "status": session.status.value,
                }
                for session, performer, agent_def in results
            ],
            "count": len(results),
        }
    finally:
        db.close()
