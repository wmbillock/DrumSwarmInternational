"""Pydantic request models for V1 API routers."""

from typing import Optional

from pydantic import BaseModel


# --- Corps ---

class GenerateIconRequest(BaseModel):
    icon_prompt: str


class CreateCorpsRequest(BaseModel):
    name: str
    mascot: Optional[str] = None
    color_scheme: Optional[dict] = None
    uniform_concept: Optional[str] = None
    philosophy: Optional[str] = ""


class CorpsFeedbackRequest(BaseModel):
    feedback: str


class CorpsThemeUpdateRequest(BaseModel):
    theme_id: Optional[str] = None
    mascot: Optional[str] = None
    uniform_concept: Optional[str] = None


class CorpsCommandRequest(BaseModel):
    command: str


class CorpsModeSwitchRequest(BaseModel):
    mode: str


class RehearsalModeSetRequest(BaseModel):
    mode: str


class HireStaffRequest(BaseModel):
    performer_id: str
    role: str


class ReleaseStaffRequest(BaseModel):
    performer_id: str
    trust_penalty: float = 0.0


# --- Design ---

class CreateThreadRequest(BaseModel):
    title: str


class PostMessageRequest(BaseModel):
    message: str
    role_hint: Optional[str] = None


class UpdateSpecRequest(BaseModel):
    content: str


# --- Seasons ---

class CreateSeasonRequest(BaseModel):
    season_id: Optional[str] = None
    name: Optional[str] = None
    metadata: Optional[dict] = None


class UpdateSeasonRequest(BaseModel):
    metadata: Optional[dict] = None


class RegisterCorpsRequest(BaseModel):
    corps_id: str


class SeasonShowRequest(BaseModel):
    show_slug: str


class SeasonAssignRequest(BaseModel):
    show_slug: str
    corps_ids: list[str]


class SeasonConfigRequest(BaseModel):
    corps_per_contest: Optional[int] = None
    required_scores: Optional[int] = None


class FinalsDeclareWinnerRequest(BaseModel):
    corps_id: str
    division: Optional[str] = None


class DraftApplyRequest(BaseModel):
    assignments: dict[str, list[str]]


# --- Competitions ---

class CreateCompetitionRequest(BaseModel):
    season_id: str
    show_slug: str
    corps_ids: list[str]


class ContestEvaluateRequest(BaseModel):
    season_id: str
    show_slug: str


# --- Critique ---

class StartCritiqueRequest(BaseModel):
    corps_id: str
    judge_type: str


class CritiqueMessageRequest(BaseModel):
    message: str


class CritiqueClarifyRequest(BaseModel):
    question: str


# --- Messaging ---

class MessagingCreateThreadRequest(BaseModel):
    originator_role: str
    subject: str
    initial_message_body: str
    initial_sender_name: Optional[str] = "Agent"
    user_role: str


class MessagingAddMessageRequest(BaseModel):
    sender_type: str
    sender_role: str
    sender_name: str
    body: str


class MessagingMarkThreadCompleteRequest(BaseModel):
    completed_by_user_id: str
    completed_by_user_role: str


class MessagingBulkArchiveRequest(BaseModel):
    thread_ids: list[str]
    archived_by_user_id: str
    archived_by_user_role: str


# --- Runs ---

class StartRunRequest(BaseModel):
    show_slug: str
    corps_id: str
    season_id: str


# --- Seance ---

class CreateSeanceRequest(BaseModel):
    corps_id: str
    entry_id: str


class SeanceMessageRequest(BaseModel):
    message: str
    mode: str = "strict"


# --- Segments & Reps ---

class SegmentCreateRequest(BaseModel):
    type: str
    title: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    caption: Optional[str] = None


class RepCreateRequest(BaseModel):
    segment_id: str


class RepTransitionRequest(BaseModel):
    new_status: str
    assigned_to: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None


# --- Scoring ---

class ScoreCreateRequest(BaseModel):
    judge_type: str
    value: float
    box: int
    rep_id: Optional[str] = None
    segment_id: Optional[str] = None
    feedback: Optional[str] = None


# --- Self-Improvement ---

class SelfImprovementProposalRequest(BaseModel):
    definition_id: str
    changes: dict
    reason: str


class ImprovementActionRequest(BaseModel):
    approver_session_id: str


# --- Memory ---

class MemoryUpdateRequest(BaseModel):
    content: str


# --- Communication ---

class MessageCreateV1Request(BaseModel):
    from_role: str
    type: str
    subject: str
    body: Optional[str] = None
    to_role: Optional[str] = None
    priority: str = "normal"
    segment_id: Optional[str] = None
