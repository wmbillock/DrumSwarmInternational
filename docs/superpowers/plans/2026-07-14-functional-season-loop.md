# Functional Season Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the DCI metaphor into an enforceable multi-competition season loop where corps hire staff, develop members, design shows, rehearse, compete repeatedly, learn from judging, and evolve across seasons.

**Architecture:** Add a season-run orchestration layer that owns phase transitions and records every phase outcome as queryable database state. Existing services for corps, performers, reps, judging, critique, drafting, and lifecycle evolution remain the domain primitives, but they become subordinate to a single authoritative season state machine. The frontend should read phase status and blockers from backend state rather than inferring progress from scattered sessions, logs, and scores.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Alembic, SQLite/Postgres-compatible schema design, pytest, React, TypeScript.

## Global Constraints

- Preserve the DCI metaphor; do not rename the domain into generic project-management terminology.
- A season contains multiple regular-season shows plus one finals event.
- Regular-season show count is configurable through backend settings/API/UI.
- Winter camp count is configurable per season but must be between `1` and `7`, representing November through May.
- Corps must improve from show to show through rehearsal and critique-driven plan changes.
- Corps, staff, and performers must evolve from season to season using recorded results, trust, experience, prestige, and memory updates.
- No corps can advance to a phase unless required artifacts and state records for the prior phase exist.
- No rep can remain pending without an assignment route or a visible blocker reason.
- Every agent session must receive a narrow mission packet with one role, one phase, one allowed work target, allowed tools, explicit forbidden scope, and a stop condition.
- Agent sessions must be blocked from creating unrelated reps, changing unrelated segments, or self-selecting new objectives outside their mission packet.
- Scores and tapes must link to the performed product they judged.
- The UI must show staff, performers, season phase, next action, blockers, and learning history.
- Tests must prove the full happy path and at least one blocked path.

---

## Current Failure Model

The audit showed that the current system has useful nouns but lacks an enforced lifecycle:

- Corps can appear without shows, segments, reps, staff, or performers.
- Performers can be linked to sessions but not record completed work, experience, or season growth.
- Competitions can produce scores that are not linked to reps or artifacts.
- Season transition and evaluation exist, but are manual endpoints rather than consequences of completion.
- Routing can strand reps when segments have no caption.
- Metronome and heartbeat loops can spam sessions without moving corps through a show day.
- Multiple DB files and SQLite lock failures make runtime state unreliable.

This plan fixes those issues by making the season loop the organizing contract.

## Target Season Loop

The implemented loop should support this canonical flow:

1. Staff hiring, firing, and training.
2. Offseason member improvement and core-memory updates from prior season results.
3. Next-season show design through the design cycle.
4. Member recruiting using prestige, cachet, ambition, ability, fit, and competitive success.
5. `1..7` winter camps for show learning and technique development, capped like a DCI November-May camp calendar.
6. `N` tour shows, where `N` comes from season settings and is visible/editable in the UI.
7. For each tour show:
   - Run basics.
   - Run visual block.
   - Run music block and sectionals.
   - Run full ensemble block.
   - Run full show run-through.
   - Compete.
   - Judges produce scores and tapes.
   - Staff react to scores and tapes.
   - Staff attend critique.
   - Corps adjusts plans based on feedback.
8. Repeat show loop until regular-season shows are complete.
9. Run finals, select winning items, crown champion, and perform end-of-season evolution.

## Domain Model Additions

### New Concepts

- `SeasonRun`: one concrete execution of a season calendar, including configured regular-show and winter-camp counts.
- `SeasonPhase`: one phase in the season run.
- `SeasonEvent`: a regular-season show or finals.
- `CorpsSeasonState`: one corps' state inside one season.
- `CorpsEventState`: one corps' state inside one show day.
- `RehearsalBlock`: basics, visual, music, sectionals, ensemble, run-through.
- `MissionPacket`: a scoped assignment that tells one agent exactly what it owns and what it must not touch.
- `JudgingTape`: judge feedback tied to a corps event performance.
- `CritiqueAdjustment`: staff response to scores and tapes.
- `LearningDelta`: recorded improvement applied to performer, staff, corps strategy, or memory.

### Required Invariants

- A `SeasonRun` cannot start tour shows until each registered corps has staff, performers, a show, captioned segments, and exactly its configured winter camp records.
- An `AgentSession` cannot start without a mission packet tied to a corps, phase, role, and specific target such as a rep, rehearsal block, critique item, or judging assignment.
- An agent cannot mutate state outside its mission packet; out-of-scope tool calls must fail with a structured blocker instead of being executed.
- A mission packet must define completion criteria and a required handoff target, so sessions stop cleanly rather than inventing follow-up work.
- A `CorpsEventState` cannot enter `competing` until basics, visual, music, ensemble, and run-through blocks have completed or produced accepted blockers.
- A `Score` created during competition must link to `season_event_id`, `corps_id`, and either `rep_id`, `artifact_id`, or `performance_id`.
- A `JudgingTape` must link to the same judged product as its score.
- A `CritiqueAdjustment` must link to at least one score caption or tape item.
- A regular-season show cannot close until critique adjustments are recorded for every competing corps.
- Finals cannot start until all regular-season events are closed.
- End-of-season evolution cannot run until finals scores, placements, and critique summaries are recorded.

---

### Task 1: Add Season Run State Models

**Files:**
- Create: `backend/models/season_run.py`
- Modify: `backend/models/__init__.py`
- Create: `backend/tests/test_season_run_models.py`

**Interfaces:**
- Produces:
  - `SeasonRun`
  - `SeasonEvent`
  - `CorpsSeasonState`
  - `CorpsEventState`
  - `SeasonRunStatus`
  - `SeasonEventType`
  - `SeasonEventStatus`
  - `CorpsSeasonPhase`
  - `CorpsEventPhase`

- [ ] **Step 1: Write failing model tests**

Create `backend/tests/test_season_run_models.py`:

```python
from backend.models.season_run import (
    CorpsEventPhase,
    CorpsEventState,
    CorpsSeasonPhase,
    CorpsSeasonState,
    SeasonEvent,
    SeasonEventStatus,
    SeasonEventType,
    SeasonRun,
    SeasonRunStatus,
)


def test_season_run_defaults():
    run = SeasonRun(name="2026 Test Season", regular_show_count=3, winter_camp_count=7)

    assert run.status == SeasonRunStatus.PLANNING
    assert run.regular_show_count == 3
    assert run.winter_camp_count == 7


def test_season_event_defaults():
    event = SeasonEvent(
        season_run_id="season-1",
        name="Midwest Regional",
        event_type=SeasonEventType.REGULAR,
        sequence_index=1,
    )

    assert event.status == SeasonEventStatus.SCHEDULED
    assert event.sequence_index == 1


def test_corps_season_state_defaults():
    state = CorpsSeasonState(
        season_run_id="season-1",
        corps_id="corps-1",
    )

    assert state.phase == CorpsSeasonPhase.STAFFING
    assert state.prestige_snapshot == 0.0
    assert state.cachet_snapshot == 0.0


def test_corps_event_state_defaults():
    state = CorpsEventState(
        season_event_id="event-1",
        corps_id="corps-1",
    )

    assert state.phase == CorpsEventPhase.NOT_STARTED
    assert state.blocker_reason is None
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_season_run_models.py -q
```

Expected: FAIL because `backend.models.season_run` does not exist.

- [ ] **Step 3: Implement models**

Create `backend/models/season_run.py`:

```python
import enum
import uuid

from sqlalchemy import Column, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class SeasonRunStatus(str, enum.Enum):
    PLANNING = "planning"
    OFFSEASON = "offseason"
    DESIGN = "design"
    RECRUITING = "recruiting"
    WINTER_CAMPS = "winter_camps"
    ON_TOUR = "on_tour"
    FINALS = "finals"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class SeasonEventType(str, enum.Enum):
    REGULAR = "regular"
    FINALS = "finals"


class SeasonEventStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    REHEARSING = "rehearsing"
    COMPETING = "competing"
    CRITIQUE = "critique"
    CLOSED = "closed"
    BLOCKED = "blocked"


class CorpsSeasonPhase(str, enum.Enum):
    STAFFING = "staffing"
    OFFSEASON_TRAINING = "offseason_training"
    DESIGNING_SHOW = "designing_show"
    RECRUITING = "recruiting"
    WINTER_CAMPS = "winter_camps"
    ON_TOUR = "on_tour"
    FINALS = "finals"
    SEASON_COMPLETE = "season_complete"
    BLOCKED = "blocked"


class CorpsEventPhase(str, enum.Enum):
    NOT_STARTED = "not_started"
    BASICS = "basics"
    VISUAL_BLOCK = "visual_block"
    MUSIC_BLOCK = "music_block"
    FULL_ENSEMBLE = "full_ensemble"
    RUN_THROUGH = "run_through"
    COMPETING = "competing"
    SCORED = "scored"
    CRITIQUE = "critique"
    ADJUSTED = "adjusted"
    CLOSED = "closed"
    BLOCKED = "blocked"


class SeasonRun(Base):
    __tablename__ = "season_runs"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    status = Column(Enum(SeasonRunStatus), nullable=False, default=SeasonRunStatus.PLANNING)
    regular_show_count = Column(Integer, nullable=False, default=3)
    winter_camp_count = Column(Integer, nullable=False, default=7)
    current_event_index = Column(Integer, nullable=False, default=0)
    blocker_reason = Column(Text, nullable=True)

    events = relationship("SeasonEvent", cascade="all, delete-orphan", back_populates="season_run")
    corps_states = relationship("CorpsSeasonState", cascade="all, delete-orphan", back_populates="season_run")


class SeasonEvent(Base):
    __tablename__ = "season_events"

    id = Column(String, primary_key=True, default=_uuid)
    season_run_id = Column(String, ForeignKey("season_runs.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    event_type = Column(Enum(SeasonEventType), nullable=False)
    status = Column(Enum(SeasonEventStatus), nullable=False, default=SeasonEventStatus.SCHEDULED)
    sequence_index = Column(Integer, nullable=False)
    blocker_reason = Column(Text, nullable=True)

    season_run = relationship("SeasonRun", back_populates="events")
    corps_event_states = relationship("CorpsEventState", cascade="all, delete-orphan", back_populates="season_event")


class CorpsSeasonState(Base):
    __tablename__ = "corps_season_states"

    id = Column(String, primary_key=True, default=_uuid)
    season_run_id = Column(String, ForeignKey("season_runs.id"), nullable=False, index=True)
    corps_id = Column(String, ForeignKey("corps.id"), nullable=False, index=True)
    phase = Column(Enum(CorpsSeasonPhase), nullable=False, default=CorpsSeasonPhase.STAFFING)
    prestige_snapshot = Column(Float, nullable=False, default=0.0)
    cachet_snapshot = Column(Float, nullable=False, default=0.0)
    blocker_reason = Column(Text, nullable=True)

    season_run = relationship("SeasonRun", back_populates="corps_states")


class CorpsEventState(Base):
    __tablename__ = "corps_event_states"

    id = Column(String, primary_key=True, default=_uuid)
    season_event_id = Column(String, ForeignKey("season_events.id"), nullable=False, index=True)
    corps_id = Column(String, ForeignKey("corps.id"), nullable=False, index=True)
    phase = Column(Enum(CorpsEventPhase), nullable=False, default=CorpsEventPhase.NOT_STARTED)
    blocker_reason = Column(Text, nullable=True)

    season_event = relationship("SeasonEvent", back_populates="corps_event_states")
```

Modify `backend/models/__init__.py` to export the new models and enums.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_season_run_models.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/models/season_run.py backend/models/__init__.py backend/tests/test_season_run_models.py
git commit -m "feat: add season run state models"
```

---

### Task 2: Add Season Calendar Builder

**Files:**
- Create: `backend/services/season_calendar.py`
- Test: `backend/tests/test_season_calendar.py`

**Interfaces:**
- Consumes:
  - `SeasonRun`
  - `SeasonEvent`
  - `SeasonEventType`
- Produces:
  - `create_season_calendar(db, *, name: str, regular_show_count: int, winter_camp_count: int, corps_ids: list[str]) -> SeasonRun`

- [ ] **Step 1: Write failing calendar tests**

Create `backend/tests/test_season_calendar.py`:

```python
from backend.models.season_run import SeasonEventType, SeasonRunStatus
from backend.services.season_calendar import create_season_calendar


def test_create_season_calendar_creates_regular_shows_and_finals(db_session):
    run = create_season_calendar(
        db_session,
        name="2026 Test Season",
        regular_show_count=2,
        winter_camp_count=7,
        corps_ids=["corps-a", "corps-b"],
    )

    assert run.status == SeasonRunStatus.PLANNING
    assert run.regular_show_count == 2
    assert run.winter_camp_count == 7
    assert [event.event_type for event in run.events] == [
        SeasonEventType.REGULAR,
        SeasonEventType.REGULAR,
        SeasonEventType.FINALS,
    ]
    assert [event.sequence_index for event in run.events] == [1, 2, 3]
    assert len(run.corps_states) == 2


def test_create_season_calendar_rejects_zero_regular_shows(db_session):
    try:
        create_season_calendar(
            db_session,
            name="Broken Season",
            regular_show_count=0,
            winter_camp_count=7,
            corps_ids=["corps-a"],
        )
    except ValueError as exc:
        assert "regular_show_count must be at least 1" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_create_season_calendar_rejects_more_than_seven_winter_camps(db_session):
    try:
        create_season_calendar(
            db_session,
            name="Too Many Camps",
            regular_show_count=3,
            winter_camp_count=8,
            corps_ids=["corps-a"],
        )
    except ValueError as exc:
        assert "winter_camp_count must be between 1 and 7" in str(exc)
    else:
        raise AssertionError("expected ValueError")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_season_calendar.py -q
```

Expected: FAIL because `backend.services.season_calendar` does not exist.

- [ ] **Step 3: Implement calendar builder**

Create `backend/services/season_calendar.py`:

```python
from sqlalchemy.orm import Session

from backend.models.season_run import (
    CorpsSeasonState,
    SeasonEvent,
    SeasonEventType,
    SeasonRun,
)


def create_season_calendar(
    db: Session,
    *,
    name: str,
    regular_show_count: int,
    winter_camp_count: int,
    corps_ids: list[str],
) -> SeasonRun:
    if regular_show_count < 1:
        raise ValueError("regular_show_count must be at least 1")
    if winter_camp_count < 1 or winter_camp_count > 7:
        raise ValueError("winter_camp_count must be between 1 and 7")
    if not corps_ids:
        raise ValueError("at least one corps is required")

    run = SeasonRun(
        name=name,
        regular_show_count=regular_show_count,
        winter_camp_count=winter_camp_count,
    )
    db.add(run)
    db.flush()

    for index in range(1, regular_show_count + 1):
        db.add(
            SeasonEvent(
                season_run_id=run.id,
                name=f"Regular Show {index}",
                event_type=SeasonEventType.REGULAR,
                sequence_index=index,
            )
        )

    db.add(
        SeasonEvent(
            season_run_id=run.id,
            name="Season Finals",
            event_type=SeasonEventType.FINALS,
            sequence_index=regular_show_count + 1,
        )
    )

    for corps_id in corps_ids:
        db.add(CorpsSeasonState(season_run_id=run.id, corps_id=corps_id))

    db.commit()
    db.refresh(run)
    return run
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_season_calendar.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/season_calendar.py backend/tests/test_season_calendar.py
git commit -m "feat: create season calendars with finals"
```

---

### Task 3: Add Corps Readiness Invariants

**Files:**
- Create: `backend/services/season_invariants.py`
- Test: `backend/tests/test_season_invariants.py`

**Interfaces:**
- Produces:
  - `SeasonBlocker(code: str, message: str, corps_id: str | None = None)`
  - `check_corps_ready_for_winter_camps(db, *, corps_id: str) -> list[SeasonBlocker]`
  - `check_corps_ready_for_tour(db, *, corps_id: str) -> list[SeasonBlocker]`
  - `check_corps_ready_to_compete(db, *, corps_id: str, season_event_id: str) -> list[SeasonBlocker]`

- [ ] **Step 1: Write failing invariant tests**

Create `backend/tests/test_season_invariants.py`:

```python
from backend.services.season_invariants import (
    SeasonBlocker,
    check_corps_ready_for_tour,
)


def test_tour_readiness_reports_missing_roster_show_and_unroutable_segments(db_session):
    blockers = check_corps_ready_for_tour(db_session, corps_id="missing-corps")

    assert SeasonBlocker(
        code="missing_corps",
        message="Corps does not exist.",
        corps_id="missing-corps",
    ) in blockers


def test_season_blocker_is_value_comparable():
    assert SeasonBlocker("x", "blocked", "c") == SeasonBlocker("x", "blocked", "c")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_season_invariants.py -q
```

Expected: FAIL because `season_invariants` does not exist.

- [ ] **Step 3: Implement invariant scaffolding**

Create `backend/services/season_invariants.py`:

```python
from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.models.corps import Corps
from backend.models.segment import Segment


@dataclass(frozen=True)
class SeasonBlocker:
    code: str
    message: str
    corps_id: str | None = None


def check_corps_ready_for_winter_camps(db: Session, *, corps_id: str) -> list[SeasonBlocker]:
    corps = db.get(Corps, corps_id)
    if corps is None:
        return [SeasonBlocker("missing_corps", "Corps does not exist.", corps_id)]

    blockers: list[SeasonBlocker] = []
    if not getattr(corps, "show_id", None):
        blockers.append(SeasonBlocker("missing_show", "Corps has no assigned show.", corps_id))

    return blockers


def check_corps_ready_for_tour(db: Session, *, corps_id: str) -> list[SeasonBlocker]:
    corps = db.get(Corps, corps_id)
    if corps is None:
        return [SeasonBlocker("missing_corps", "Corps does not exist.", corps_id)]

    blockers = check_corps_ready_for_winter_camps(db, corps_id=corps_id)
    if not _has_routable_segments(db, corps):
        blockers.append(
            SeasonBlocker(
                "unroutable_segments",
                "Corps show has segments without captions or fallback owners.",
                corps_id,
            )
        )

    return blockers


def check_corps_ready_to_compete(
    db: Session,
    *,
    corps_id: str,
    season_event_id: str,
) -> list[SeasonBlocker]:
    blockers = check_corps_ready_for_tour(db, corps_id=corps_id)
    return blockers


def _has_routable_segments(db: Session, corps: Corps) -> bool:
    show_id = getattr(corps, "show_id", None)
    if not show_id:
        return False

    segments = db.query(Segment).filter(Segment.show_id == show_id).all()
    if not segments:
        return False

    return all(segment.caption or segment.assigned_role for segment in segments)
```

- [ ] **Step 4: Expand tests to cover real corps fixtures**

Add fixtures using the local factories in `backend/tests/conftest.py`. Assert:

```python
def test_tour_readiness_blocks_uncaptioned_segments(db_session, corps_factory, show_factory, segment_factory):
    corps = corps_factory()
    show = show_factory()
    corps.show_id = show.id
    segment_factory(show_id=show.id, caption=None, assigned_role=None)
    db_session.commit()

    blockers = check_corps_ready_for_tour(db_session, corps_id=corps.id)

    assert [blocker.code for blocker in blockers] == ["unroutable_segments"]
```

- [ ] **Step 5: Run tests**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_season_invariants.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/services/season_invariants.py backend/tests/test_season_invariants.py
git commit -m "feat: enforce season readiness invariants"
```

---

### Task 4: Implement Offseason Learning and Staff Training Phase

**Files:**
- Create: `backend/services/season_phases/offseason.py`
- Modify: `backend/services/lifecycle_manager.py`
- Test: `backend/tests/test_offseason_phase.py`

**Interfaces:**
- Produces:
  - `run_offseason_training(db, *, season_run_id: str, corps_id: str) -> list[LearningDelta]`
  - `LearningDelta(target_type: str, target_id: str, source: str, summary: str)`

- [ ] **Step 1: Write failing offseason tests**

Create `backend/tests/test_offseason_phase.py`:

```python
from backend.services.season_phases.offseason import run_offseason_training


def test_offseason_training_records_member_learning(db_session, performer_factory, corps_factory, season_run_factory):
    corps = corps_factory()
    performer = performer_factory(corps_id=corps.id, experience_seasons=1, trust_score=55.0)
    run = season_run_factory()

    deltas = run_offseason_training(db_session, season_run_id=run.id, corps_id=corps.id)

    db_session.refresh(performer)
    assert deltas
    assert performer.trust_score > 55.0
    assert any(delta.target_id == performer.id for delta in deltas)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_offseason_phase.py -q
```

Expected: FAIL because `season_phases.offseason` does not exist.

- [ ] **Step 3: Implement offseason phase**

Create `backend/services/season_phases/offseason.py`:

```python
from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.models.performer import Performer


@dataclass(frozen=True)
class LearningDelta:
    target_type: str
    target_id: str
    source: str
    summary: str


def run_offseason_training(db: Session, *, season_run_id: str, corps_id: str) -> list[LearningDelta]:
    performers = db.query(Performer).filter(Performer.corps_id == corps_id).all()
    deltas: list[LearningDelta] = []

    for performer in performers:
        old_trust = float(performer.trust_score or 0.0)
        performer.trust_score = min(100.0, old_trust + 1.0)
        deltas.append(
            LearningDelta(
                target_type="performer",
                target_id=performer.id,
                source="offseason_training",
                summary=f"Offseason training improved trust from {old_trust:.1f} to {performer.trust_score:.1f}.",
            )
        )

    db.commit()
    return deltas
```

- [ ] **Step 4: Run tests**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_offseason_phase.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/season_phases/offseason.py backend/tests/test_offseason_phase.py
git commit -m "feat: record offseason learning"
```

---

### Task 5: Wire Show Design Completion Into Season Progression

**Files:**
- Create: `backend/services/season_phases/design.py`
- Modify: `backend/services/show_service.py`
- Modify: `backend/services/show_persistence.py`
- Test: `backend/tests/test_season_design_phase.py`

**Interfaces:**
- Produces:
  - `complete_show_design_for_season(db, *, season_run_id: str, corps_id: str, show_id: str) -> CorpsSeasonState`

- [ ] **Step 1: Write failing design phase test**

Create `backend/tests/test_season_design_phase.py`:

```python
from backend.models.season_run import CorpsSeasonPhase
from backend.services.season_phases.design import complete_show_design_for_season


def test_complete_show_design_advances_corps_to_recruiting(db_session, corps_factory, season_run_factory, show_factory):
    corps = corps_factory()
    run = season_run_factory(corps_ids=[corps.id])
    show = show_factory()

    state = complete_show_design_for_season(
        db_session,
        season_run_id=run.id,
        corps_id=corps.id,
        show_id=show.id,
    )

    assert state.phase == CorpsSeasonPhase.RECRUITING
    db_session.refresh(corps)
    assert corps.show_id == show.id
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_season_design_phase.py -q
```

Expected: FAIL because design phase service does not exist.

- [ ] **Step 3: Implement design phase service**

Create `backend/services/season_phases/design.py`:

```python
from sqlalchemy.orm import Session

from backend.models.corps import Corps
from backend.models.season_run import CorpsSeasonPhase, CorpsSeasonState


def complete_show_design_for_season(
    db: Session,
    *,
    season_run_id: str,
    corps_id: str,
    show_id: str,
) -> CorpsSeasonState:
    corps = db.get(Corps, corps_id)
    if corps is None:
        raise ValueError("Corps does not exist.")

    state = (
        db.query(CorpsSeasonState)
        .filter(
            CorpsSeasonState.season_run_id == season_run_id,
            CorpsSeasonState.corps_id == corps_id,
        )
        .one()
    )

    corps.show_id = show_id
    state.phase = CorpsSeasonPhase.RECRUITING
    state.blocker_reason = None
    db.commit()
    db.refresh(state)
    return state
```

- [ ] **Step 4: Run tests**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_season_design_phase.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/season_phases/design.py backend/tests/test_season_design_phase.py
git commit -m "feat: connect show design to season progression"
```

---

### Task 6: Make Recruiting Use Prestige and Roster Needs

**Files:**
- Modify: `backend/services/performer_service.py`
- Modify: `backend/services/drafting.py`
- Create: `backend/services/season_phases/recruiting.py`
- Test: `backend/tests/test_recruiting_phase.py`

**Interfaces:**
- Produces:
  - `run_season_recruiting(db, *, season_run_id: str, corps_id: str, open_roles: list[str]) -> list[Performer]`

- [ ] **Step 1: Write failing recruiting test**

Create `backend/tests/test_recruiting_phase.py`:

```python
from backend.models.season_run import CorpsSeasonPhase
from backend.services.season_phases.recruiting import run_season_recruiting


def test_recruiting_fills_open_roles_and_advances_to_winter_camps(db_session, corps_factory, season_run_factory):
    corps = corps_factory(prestige=80.0)
    run = season_run_factory(corps_ids=[corps.id])

    performers = run_season_recruiting(
        db_session,
        season_run_id=run.id,
        corps_id=corps.id,
        open_roles=["brass_caption_head", "percussion_caption_head"],
    )

    assert {performer.role for performer in performers} == {"brass_caption_head", "percussion_caption_head"}
    state = run.corps_states[0]
    db_session.refresh(state)
    assert state.phase == CorpsSeasonPhase.WINTER_CAMPS
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_recruiting_phase.py -q
```

Expected: FAIL because recruiting phase service does not exist.

- [ ] **Step 3: Implement recruiting phase**

Create `backend/services/season_phases/recruiting.py`:

```python
from sqlalchemy.orm import Session

from backend.models.performer import Performer
from backend.models.season_run import CorpsSeasonPhase, CorpsSeasonState
from backend.services.performer_service import audition_for_role


def run_season_recruiting(
    db: Session,
    *,
    season_run_id: str,
    corps_id: str,
    open_roles: list[str],
) -> list[Performer]:
    if not open_roles:
        raise ValueError("open_roles must not be empty")

    recruited: list[Performer] = []
    for role in open_roles:
        recruited.append(audition_for_role(db, corps_id=corps_id, role=role))

    state = (
        db.query(CorpsSeasonState)
        .filter(
            CorpsSeasonState.season_run_id == season_run_id,
            CorpsSeasonState.corps_id == corps_id,
        )
        .one()
    )
    state.phase = CorpsSeasonPhase.WINTER_CAMPS
    state.blocker_reason = None
    db.commit()
    return recruited
```

- [ ] **Step 4: Add prestige-aware candidate ordering**

Modify `backend/services/performer_service.py` so `audition_for_role` accepts optional `prestige: float | None = None` and uses it to bias candidate quality:

```python
def audition_for_role(
    db: Session,
    *,
    corps_id: str,
    role: str,
    prestige: float | None = None,
) -> Performer:
    trust_boost = 0.0 if prestige is None else min(10.0, max(0.0, prestige / 10.0))
    performer = Performer(
        corps_id=corps_id,
        role=role,
        trust_score=50.0 + trust_boost,
    )
    db.add(performer)
    db.flush()
    return performer
```

Then pass corps prestige from `run_season_recruiting`.

- [ ] **Step 5: Run recruiting tests**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_recruiting_phase.py backend/tests/test_performers.py backend/tests/test_drafting.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/services/season_phases/recruiting.py backend/services/performer_service.py backend/services/drafting.py backend/tests/test_recruiting_phase.py
git commit -m "feat: recruit season performers using corps prestige"
```

---

### Task 7: Implement Winter Camps as Rehearsal Blocks

**Files:**
- Create: `backend/models/rehearsal_block.py`
- Create: `backend/services/season_phases/winter_camps.py`
- Modify: `backend/models/__init__.py`
- Test: `backend/tests/test_winter_camps_phase.py`

**Interfaces:**
- Produces:
  - `RehearsalBlock`
  - `RehearsalBlockType`
  - `RehearsalBlockStatus`
  - `run_winter_camps(db, *, season_run_id: str, corps_id: str, camp_count: int) -> list[RehearsalBlock]`

- [ ] **Step 1: Write failing winter camp test**

Create `backend/tests/test_winter_camps_phase.py`:

```python
from backend.models.rehearsal_block import RehearsalBlockStatus, RehearsalBlockType
from backend.models.season_run import CorpsSeasonPhase
from backend.services.season_phases.winter_camps import run_winter_camps


def test_winter_camps_create_learning_blocks_and_advance_to_tour(db_session, corps_factory, season_run_factory):
    corps = corps_factory()
    run = season_run_factory(corps_ids=[corps.id])

    blocks = run_winter_camps(db_session, season_run_id=run.id, corps_id=corps.id, camp_count=2)

    assert len(blocks) == 2
    assert all(block.block_type == RehearsalBlockType.WINTER_CAMP for block in blocks)
    assert all(block.status == RehearsalBlockStatus.COMPLETED for block in blocks)
    state = run.corps_states[0]
    db_session.refresh(state)
    assert state.phase == CorpsSeasonPhase.ON_TOUR


def test_winter_camps_reject_more_than_seven_camps(db_session, corps_factory, season_run_factory):
    corps = corps_factory()
    run = season_run_factory(corps_ids=[corps.id])

    try:
        run_winter_camps(db_session, season_run_id=run.id, corps_id=corps.id, camp_count=8)
    except ValueError as exc:
        assert "camp_count must be between 1 and 7" in str(exc)
    else:
        raise AssertionError("expected ValueError")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_winter_camps_phase.py -q
```

Expected: FAIL because rehearsal block model does not exist.

- [ ] **Step 3: Implement rehearsal block model and phase service**

Create `backend/models/rehearsal_block.py`:

```python
import enum
import uuid

from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Text

from backend.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class RehearsalBlockType(str, enum.Enum):
    WINTER_CAMP = "winter_camp"
    BASICS = "basics"
    VISUAL_BLOCK = "visual_block"
    MUSIC_BLOCK = "music_block"
    SECTIONAL = "sectional"
    FULL_ENSEMBLE = "full_ensemble"
    RUN_THROUGH = "run_through"


class RehearsalBlockStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class RehearsalBlock(Base):
    __tablename__ = "rehearsal_blocks"

    id = Column(String, primary_key=True, default=_uuid)
    season_run_id = Column(String, ForeignKey("season_runs.id"), nullable=False, index=True)
    season_event_id = Column(String, ForeignKey("season_events.id"), nullable=True, index=True)
    corps_id = Column(String, ForeignKey("corps.id"), nullable=False, index=True)
    block_type = Column(Enum(RehearsalBlockType), nullable=False)
    status = Column(Enum(RehearsalBlockStatus), nullable=False, default=RehearsalBlockStatus.SCHEDULED)
    sequence_index = Column(Integer, nullable=False, default=1)
    summary = Column(Text, nullable=True)
```

Create `backend/services/season_phases/winter_camps.py`:

```python
from sqlalchemy.orm import Session

from backend.models.rehearsal_block import RehearsalBlock, RehearsalBlockStatus, RehearsalBlockType
from backend.models.season_run import CorpsSeasonPhase, CorpsSeasonState


def run_winter_camps(
    db: Session,
    *,
    season_run_id: str,
    corps_id: str,
    camp_count: int,
) -> list[RehearsalBlock]:
    if camp_count < 1 or camp_count > 7:
        raise ValueError("camp_count must be between 1 and 7")

    blocks: list[RehearsalBlock] = []
    for index in range(1, camp_count + 1):
        block = RehearsalBlock(
            season_run_id=season_run_id,
            corps_id=corps_id,
            block_type=RehearsalBlockType.WINTER_CAMP,
            status=RehearsalBlockStatus.COMPLETED,
            sequence_index=index,
            summary=f"Winter camp {index} completed.",
        )
        db.add(block)
        blocks.append(block)

    state = (
        db.query(CorpsSeasonState)
        .filter(
            CorpsSeasonState.season_run_id == season_run_id,
            CorpsSeasonState.corps_id == corps_id,
        )
        .one()
    )
    state.phase = CorpsSeasonPhase.ON_TOUR
    state.blocker_reason = None
    db.commit()
    return blocks
```

- [ ] **Step 4: Run tests**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_winter_camps_phase.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/models/rehearsal_block.py backend/models/__init__.py backend/services/season_phases/winter_camps.py backend/tests/test_winter_camps_phase.py
git commit -m "feat: model winter camps as rehearsal blocks"
```

---

### Task 8: Implement Per-Show Rehearsal Sequence

**Files:**
- Create: `backend/services/season_phases/show_day.py`
- Test: `backend/tests/test_show_day_phase.py`

**Interfaces:**
- Produces:
  - `run_show_day_rehearsal(db, *, season_run_id: str, season_event_id: str, corps_id: str) -> CorpsEventState`

- [ ] **Step 1: Write failing show-day rehearsal test**

Create `backend/tests/test_show_day_phase.py`:

```python
from backend.models.rehearsal_block import RehearsalBlock, RehearsalBlockStatus, RehearsalBlockType
from backend.models.season_run import CorpsEventPhase
from backend.services.season_phases.show_day import run_show_day_rehearsal


def test_show_day_rehearsal_runs_required_blocks_in_order(db_session, corps_factory, season_run_factory):
    corps = corps_factory()
    run = season_run_factory(corps_ids=[corps.id], regular_show_count=1)
    event = run.events[0]

    state = run_show_day_rehearsal(
        db_session,
        season_run_id=run.id,
        season_event_id=event.id,
        corps_id=corps.id,
    )

    blocks = (
        db_session.query(RehearsalBlock)
        .filter(RehearsalBlock.season_event_id == event.id)
        .order_by(RehearsalBlock.sequence_index)
        .all()
    )
    assert [block.block_type for block in blocks] == [
        RehearsalBlockType.BASICS,
        RehearsalBlockType.VISUAL_BLOCK,
        RehearsalBlockType.MUSIC_BLOCK,
        RehearsalBlockType.SECTIONAL,
        RehearsalBlockType.FULL_ENSEMBLE,
        RehearsalBlockType.RUN_THROUGH,
    ]
    assert all(block.status == RehearsalBlockStatus.COMPLETED for block in blocks)
    assert state.phase == CorpsEventPhase.RUN_THROUGH
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_show_day_phase.py -q
```

Expected: FAIL because show-day phase service does not exist.

- [ ] **Step 3: Implement show-day rehearsal sequence**

Create `backend/services/season_phases/show_day.py`:

```python
from sqlalchemy.orm import Session

from backend.models.rehearsal_block import RehearsalBlock, RehearsalBlockStatus, RehearsalBlockType
from backend.models.season_run import CorpsEventPhase, CorpsEventState


SHOW_DAY_BLOCKS = [
    RehearsalBlockType.BASICS,
    RehearsalBlockType.VISUAL_BLOCK,
    RehearsalBlockType.MUSIC_BLOCK,
    RehearsalBlockType.SECTIONAL,
    RehearsalBlockType.FULL_ENSEMBLE,
    RehearsalBlockType.RUN_THROUGH,
]


def run_show_day_rehearsal(
    db: Session,
    *,
    season_run_id: str,
    season_event_id: str,
    corps_id: str,
) -> CorpsEventState:
    state = _get_or_create_event_state(db, season_event_id=season_event_id, corps_id=corps_id)

    for index, block_type in enumerate(SHOW_DAY_BLOCKS, start=1):
        db.add(
            RehearsalBlock(
                season_run_id=season_run_id,
                season_event_id=season_event_id,
                corps_id=corps_id,
                block_type=block_type,
                status=RehearsalBlockStatus.COMPLETED,
                sequence_index=index,
                summary=f"{block_type.value} completed.",
            )
        )

    state.phase = CorpsEventPhase.RUN_THROUGH
    state.blocker_reason = None
    db.commit()
    db.refresh(state)
    return state


def _get_or_create_event_state(db: Session, *, season_event_id: str, corps_id: str) -> CorpsEventState:
    state = (
        db.query(CorpsEventState)
        .filter(
            CorpsEventState.season_event_id == season_event_id,
            CorpsEventState.corps_id == corps_id,
        )
        .one_or_none()
    )
    if state is not None:
        return state

    state = CorpsEventState(season_event_id=season_event_id, corps_id=corps_id)
    db.add(state)
    db.flush()
    return state
```

- [ ] **Step 4: Run tests**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_show_day_phase.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/season_phases/show_day.py backend/tests/test_show_day_phase.py
git commit -m "feat: run show-day rehearsal sequence"
```

---

### Task 9: Enforce Agent Mission Packets

**Files:**
- Create: `backend/models/mission_packet.py`
- Create: `backend/services/mission_packet_service.py`
- Modify: `backend/services/agent_runtime.py`
- Modify: `backend/services/tool_executor.py`
- Modify: `backend/models/__init__.py`
- Test: `backend/tests/test_mission_packets.py`

**Interfaces:**
- Produces:
  - `MissionPacket`
  - `MissionScopeViolation`
  - `create_mission_packet(db, *, session_id: str, corps_id: str, role: str, phase: str, target_type: str, target_id: str, allowed_tools: list[str], forbidden_scope: list[str], completion_criteria: str, handoff_target: str | None) -> MissionPacket`
  - `assert_tool_call_in_scope(db, *, session_id: str, tool_name: str, arguments: dict) -> None`

- [ ] **Step 1: Write failing mission packet tests**

Create `backend/tests/test_mission_packets.py`:

```python
import pytest

from backend.services.mission_packet_service import (
    MissionScopeViolation,
    assert_tool_call_in_scope,
    create_mission_packet,
)


def test_mission_packet_records_narrow_assignment(db_session, agent_session_factory):
    session = agent_session_factory(corps_id="corps-1", role="visual_caption_head")

    packet = create_mission_packet(
        db_session,
        session_id=session.id,
        corps_id="corps-1",
        role="visual_caption_head",
        phase="visual_block",
        target_type="rehearsal_block",
        target_id="block-1",
        allowed_tools=["submit_handoff", "update_rehearsal_block"],
        forbidden_scope=["music_block", "staffing", "unassigned_reps"],
        completion_criteria="Submit one visual-block rehearsal summary for block-1.",
        handoff_target="program_coordinator",
    )

    assert packet.session_id == session.id
    assert packet.target_type == "rehearsal_block"
    assert packet.target_id == "block-1"
    assert packet.completion_criteria == "Submit one visual-block rehearsal summary for block-1."


def test_tool_call_outside_allowed_tools_is_blocked(db_session, agent_session_factory):
    session = agent_session_factory(corps_id="corps-1", role="visual_caption_head")
    create_mission_packet(
        db_session,
        session_id=session.id,
        corps_id="corps-1",
        role="visual_caption_head",
        phase="visual_block",
        target_type="rehearsal_block",
        target_id="block-1",
        allowed_tools=["update_rehearsal_block"],
        forbidden_scope=["music_block"],
        completion_criteria="Update block-1 only.",
        handoff_target=None,
    )

    with pytest.raises(MissionScopeViolation, match="Tool submit_handoff is not allowed"):
        assert_tool_call_in_scope(
            db_session,
            session_id=session.id,
            tool_name="submit_handoff",
            arguments={"target_id": "block-1"},
        )


def test_tool_call_against_wrong_target_is_blocked(db_session, agent_session_factory):
    session = agent_session_factory(corps_id="corps-1", role="percussion_caption_head")
    create_mission_packet(
        db_session,
        session_id=session.id,
        corps_id="corps-1",
        role="percussion_caption_head",
        phase="music_block",
        target_type="rep",
        target_id="rep-1",
        allowed_tools=["update_rep"],
        forbidden_scope=["visual_block", "show_design"],
        completion_criteria="Update rep-1 only.",
        handoff_target="music_judge",
    )

    with pytest.raises(MissionScopeViolation, match="Target rep-2 is outside mission scope"):
        assert_tool_call_in_scope(
            db_session,
            session_id=session.id,
            tool_name="update_rep",
            arguments={"rep_id": "rep-2"},
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_mission_packets.py -q
```

Expected: FAIL because mission packets do not exist.

- [ ] **Step 3: Add mission packet model**

Create `backend/models/mission_packet.py`:

```python
import uuid

from sqlalchemy import Column, ForeignKey, JSON, String, Text

from backend.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class MissionPacket(Base):
    __tablename__ = "mission_packets"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("agent_sessions.id"), nullable=False, index=True, unique=True)
    corps_id = Column(String, ForeignKey("corps.id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    phase = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    target_id = Column(String, nullable=False, index=True)
    allowed_tools = Column(JSON, nullable=False, default=list)
    forbidden_scope = Column(JSON, nullable=False, default=list)
    completion_criteria = Column(Text, nullable=False)
    handoff_target = Column(String, nullable=True)
```

Modify `backend/models/__init__.py` to export `MissionPacket`.

- [ ] **Step 4: Implement mission packet service**

Create `backend/services/mission_packet_service.py`:

```python
from sqlalchemy.orm import Session

from backend.models.mission_packet import MissionPacket


class MissionScopeViolation(Exception):
    pass


TARGET_ARGUMENT_KEYS = {
    "rep": ["rep_id", "target_id"],
    "rehearsal_block": ["rehearsal_block_id", "block_id", "target_id"],
    "critique_adjustment": ["critique_adjustment_id", "adjustment_id", "target_id"],
    "judging_assignment": ["judging_assignment_id", "target_id"],
}


def create_mission_packet(
    db: Session,
    *,
    session_id: str,
    corps_id: str,
    role: str,
    phase: str,
    target_type: str,
    target_id: str,
    allowed_tools: list[str],
    forbidden_scope: list[str],
    completion_criteria: str,
    handoff_target: str | None,
) -> MissionPacket:
    if not completion_criteria.strip():
        raise ValueError("completion_criteria is required")
    if not allowed_tools:
        raise ValueError("allowed_tools must not be empty")

    packet = MissionPacket(
        session_id=session_id,
        corps_id=corps_id,
        role=role,
        phase=phase,
        target_type=target_type,
        target_id=target_id,
        allowed_tools=allowed_tools,
        forbidden_scope=forbidden_scope,
        completion_criteria=completion_criteria,
        handoff_target=handoff_target,
    )
    db.add(packet)
    db.commit()
    db.refresh(packet)
    return packet


def assert_tool_call_in_scope(
    db: Session,
    *,
    session_id: str,
    tool_name: str,
    arguments: dict,
) -> None:
    packet = db.query(MissionPacket).filter(MissionPacket.session_id == session_id).one_or_none()
    if packet is None:
        raise MissionScopeViolation("Agent session has no mission packet.")

    if tool_name not in packet.allowed_tools:
        raise MissionScopeViolation(f"Tool {tool_name} is not allowed for this mission.")

    argument_target = _extract_target_argument(packet.target_type, arguments)
    if argument_target is not None and argument_target != packet.target_id:
        raise MissionScopeViolation(f"Target {argument_target} is outside mission scope.")


def _extract_target_argument(target_type: str, arguments: dict) -> str | None:
    for key in TARGET_ARGUMENT_KEYS.get(target_type, ["target_id"]):
        if key in arguments:
            return str(arguments[key])
    return None
```

- [ ] **Step 5: Enforce packet checks in tool execution**

Modify `backend/services/tool_executor.py` at the entry point where a session executes a tool:

```python
from backend.services.mission_packet_service import MissionScopeViolation, assert_tool_call_in_scope


try:
    assert_tool_call_in_scope(
        db,
        session_id=session_id,
        tool_name=tool_name,
        arguments=arguments,
    )
except MissionScopeViolation as exc:
    return {
        "ok": False,
        "blocked": True,
        "blocker_code": "mission_scope_violation",
        "message": str(exc),
    }
```

Keep existing tool execution behavior unchanged after the scope check passes.

- [ ] **Step 6: Inject mission packet into agent prompts**

Modify `backend/services/agent_runtime.py` when building the session prompt:

```python
def render_mission_packet(packet: MissionPacket) -> str:
    return (
        "MISSION PACKET\n"
        f"Role: {packet.role}\n"
        f"Phase: {packet.phase}\n"
        f"Target: {packet.target_type}:{packet.target_id}\n"
        f"Allowed tools: {', '.join(packet.allowed_tools)}\n"
        f"Forbidden scope: {', '.join(packet.forbidden_scope)}\n"
        f"Completion criteria: {packet.completion_criteria}\n"
        f"Handoff target: {packet.handoff_target or 'none'}\n"
        "Do not create new objectives. Do not work outside the target. "
        "When completion criteria are satisfied, stop and hand off exactly as directed."
    )
```

Prepend this text after the role identity and before phase instructions.

- [ ] **Step 7: Run tests**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_mission_packets.py backend/tests/test_tool_executor.py backend/tests/test_agent_phases.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/models/mission_packet.py backend/models/__init__.py backend/services/mission_packet_service.py backend/services/agent_runtime.py backend/services/tool_executor.py backend/tests/test_mission_packets.py
git commit -m "feat: constrain agents with mission packets"
```

---

### Task 10: Link Competition Scores and Tapes to Judged Product

**Files:**
- Modify: `backend/models/score.py`
- Create: `backend/models/judging_tape.py`
- Modify: `backend/services/competition_executor.py`
- Modify: `backend/services/judge_service.py`
- Test: `backend/tests/test_competition_product_links.py`

**Interfaces:**
- Produces:
  - `JudgingTape`
  - `record_competition_result(db, *, season_event_id: str, corps_id: str, rep_id: str | None, artifact_id: str | None, score_payload: dict, tape_text: str) -> CompetitionResult`

- [ ] **Step 1: Write failing product-link test**

Create `backend/tests/test_competition_product_links.py`:

```python
from backend.models.judging_tape import JudgingTape
from backend.models.score import Score
from backend.services.competition_executor import record_competition_result


def test_competition_result_links_score_and_tape_to_rep(db_session, corps_factory, season_run_factory, rep_factory):
    corps = corps_factory()
    run = season_run_factory(corps_ids=[corps.id], regular_show_count=1)
    event = run.events[0]
    rep = rep_factory()

    record_competition_result(
        db_session,
        season_event_id=event.id,
        corps_id=corps.id,
        rep_id=rep.id,
        artifact_id=None,
        score_payload={"caption": "general_effect", "value": 82.5},
        tape_text="Strong idea; tighten execution before next show.",
    )

    score = db_session.query(Score).one()
    tape = db_session.query(JudgingTape).one()
    assert score.rep_id == rep.id
    assert score.season_event_id == event.id
    assert tape.rep_id == rep.id
    assert tape.season_event_id == event.id
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_competition_product_links.py -q
```

Expected: FAIL because score/tape product links do not exist.

- [ ] **Step 3: Add score link columns and judging tape model**

Add nullable columns to `Score`:

```python
season_event_id = Column(String, ForeignKey("season_events.id"), nullable=True, index=True)
artifact_id = Column(String, nullable=True, index=True)
```

Create `backend/models/judging_tape.py`:

```python
import uuid

from sqlalchemy import Column, ForeignKey, String, Text

from backend.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class JudgingTape(Base):
    __tablename__ = "judging_tapes"

    id = Column(String, primary_key=True, default=_uuid)
    season_event_id = Column(String, ForeignKey("season_events.id"), nullable=False, index=True)
    corps_id = Column(String, ForeignKey("corps.id"), nullable=False, index=True)
    rep_id = Column(String, ForeignKey("reps.id"), nullable=True, index=True)
    artifact_id = Column(String, nullable=True, index=True)
    caption = Column(String, nullable=False)
    tape_text = Column(Text, nullable=False)
```

- [ ] **Step 4: Implement record function**

Modify `backend/services/competition_executor.py`:

```python
from dataclasses import dataclass

from backend.models.judging_tape import JudgingTape
from backend.models.score import Score


@dataclass(frozen=True)
class CompetitionResult:
    score: Score
    tape: JudgingTape


def record_competition_result(
    db: Session,
    *,
    season_event_id: str,
    corps_id: str,
    rep_id: str | None,
    artifact_id: str | None,
    score_payload: dict,
    tape_text: str,
) -> CompetitionResult:
    if rep_id is None and artifact_id is None:
        raise ValueError("Competition result must link to rep_id or artifact_id.")

    caption = str(score_payload["caption"])
    value = float(score_payload["value"])
    score = Score(
        corps_id=corps_id,
        rep_id=rep_id,
        season_event_id=season_event_id,
        artifact_id=artifact_id,
        caption=caption,
        value=value,
    )
    tape = JudgingTape(
        season_event_id=season_event_id,
        corps_id=corps_id,
        rep_id=rep_id,
        artifact_id=artifact_id,
        caption=caption,
        tape_text=tape_text,
    )
    db.add(score)
    db.add(tape)
    db.commit()
    return CompetitionResult(score=score, tape=tape)
```

- [ ] **Step 5: Run tests**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_competition_product_links.py backend/tests/test_scoring_persistence.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/models/score.py backend/models/judging_tape.py backend/models/__init__.py backend/services/competition_executor.py backend/services/judge_service.py backend/tests/test_competition_product_links.py
git commit -m "feat: link competition scores and tapes to judged work"
```

---

### Task 11: Implement Critique Adjustments and Between-Show Learning

**Files:**
- Create: `backend/models/critique_adjustment.py`
- Create: `backend/services/season_phases/critique_learning.py`
- Modify: `backend/services/evaluation_service.py`
- Test: `backend/tests/test_critique_learning_phase.py`

**Interfaces:**
- Produces:
  - `CritiqueAdjustment`
  - `process_show_critique(db, *, season_event_id: str, corps_id: str) -> list[CritiqueAdjustment]`

- [ ] **Step 1: Write failing critique learning test**

Create `backend/tests/test_critique_learning_phase.py`:

```python
from backend.models.critique_adjustment import CritiqueAdjustment
from backend.models.season_run import CorpsEventPhase
from backend.services.competition_executor import record_competition_result
from backend.services.season_phases.critique_learning import process_show_critique


def test_critique_creates_adjustments_and_advances_event_state(db_session, corps_factory, season_run_factory, rep_factory):
    corps = corps_factory()
    run = season_run_factory(corps_ids=[corps.id], regular_show_count=1)
    event = run.events[0]
    rep = rep_factory()
    record_competition_result(
        db_session,
        season_event_id=event.id,
        corps_id=corps.id,
        rep_id=rep.id,
        artifact_id=None,
        score_payload={"caption": "visual", "value": 71.0},
        tape_text="Forms read late; improve interval clarity.",
    )

    adjustments = process_show_critique(db_session, season_event_id=event.id, corps_id=corps.id)

    assert len(adjustments) == 1
    assert db_session.query(CritiqueAdjustment).count() == 1
    assert adjustments[0].caption == "visual"
    assert adjustments[0].action_summary
    assert adjustments[0].event_state.phase == CorpsEventPhase.ADJUSTED
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_critique_learning_phase.py -q
```

Expected: FAIL because critique adjustment model/service does not exist.

- [ ] **Step 3: Implement critique adjustment model and service**

Create `backend/models/critique_adjustment.py`:

```python
import uuid

from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class CritiqueAdjustment(Base):
    __tablename__ = "critique_adjustments"

    id = Column(String, primary_key=True, default=_uuid)
    season_event_id = Column(String, ForeignKey("season_events.id"), nullable=False, index=True)
    corps_id = Column(String, ForeignKey("corps.id"), nullable=False, index=True)
    corps_event_state_id = Column(String, ForeignKey("corps_event_states.id"), nullable=False, index=True)
    caption = Column(String, nullable=False)
    source_tape_id = Column(String, ForeignKey("judging_tapes.id"), nullable=False, index=True)
    action_summary = Column(Text, nullable=False)

    event_state = relationship("CorpsEventState")
```

Create `backend/services/season_phases/critique_learning.py`:

```python
from sqlalchemy.orm import Session

from backend.models.critique_adjustment import CritiqueAdjustment
from backend.models.judging_tape import JudgingTape
from backend.models.season_run import CorpsEventPhase, CorpsEventState


def process_show_critique(
    db: Session,
    *,
    season_event_id: str,
    corps_id: str,
) -> list[CritiqueAdjustment]:
    state = (
        db.query(CorpsEventState)
        .filter(
            CorpsEventState.season_event_id == season_event_id,
            CorpsEventState.corps_id == corps_id,
        )
        .one()
    )

    tapes = (
        db.query(JudgingTape)
        .filter(
            JudgingTape.season_event_id == season_event_id,
            JudgingTape.corps_id == corps_id,
        )
        .all()
    )
    if not tapes:
        raise ValueError("Cannot process critique without judging tapes.")

    adjustments: list[CritiqueAdjustment] = []
    for tape in tapes:
        adjustment = CritiqueAdjustment(
            season_event_id=season_event_id,
            corps_id=corps_id,
            corps_event_state_id=state.id,
            caption=tape.caption,
            source_tape_id=tape.id,
            action_summary=f"Next rehearsal plan for {tape.caption}: {tape.tape_text}",
        )
        db.add(adjustment)
        adjustments.append(adjustment)

    state.phase = CorpsEventPhase.ADJUSTED
    state.blocker_reason = None
    db.commit()
    return adjustments
```

- [ ] **Step 4: Run tests**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_critique_learning_phase.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/models/critique_adjustment.py backend/models/__init__.py backend/services/season_phases/critique_learning.py backend/tests/test_critique_learning_phase.py
git commit -m "feat: record critique adjustments between shows"
```

---

### Task 12: Add Season Orchestrator Happy Path

**Files:**
- Create: `backend/services/season_orchestrator.py`
- Modify: `backend/api/v1/seasons.py`
- Test: `backend/tests/test_season_orchestrator.py`

**Interfaces:**
- Produces:
  - `run_next_season_step(db, *, season_run_id: str) -> SeasonRun`
  - `run_full_season_dry_run(db, *, season_run_id: str) -> SeasonRun`

- [ ] **Step 1: Write failing full-season test**

Create `backend/tests/test_season_orchestrator.py`:

```python
from backend.models.season_run import CorpsSeasonPhase, SeasonRunStatus
from backend.services.season_orchestrator import run_full_season_dry_run


def test_full_season_runs_multiple_shows_finals_and_evolution(db_session, corps_factory, season_calendar_factory):
    corps_a = corps_factory()
    corps_b = corps_factory()
    run = season_calendar_factory(
        corps_ids=[corps_a.id, corps_b.id],
        regular_show_count=2,
        winter_camp_count=4,
    )

    completed = run_full_season_dry_run(db_session, season_run_id=run.id)

    assert completed.status == SeasonRunStatus.COMPLETE
    assert completed.regular_show_count == 2
    assert completed.winter_camp_count == 4
    assert all(state.phase == CorpsSeasonPhase.SEASON_COMPLETE for state in completed.corps_states)
    assert len(completed.events) == 3
    assert all(event.status.value == "closed" for event in completed.events)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_season_orchestrator.py -q
```

Expected: FAIL because `season_orchestrator` does not exist.

- [ ] **Step 3: Implement orchestrator dry run**

Create `backend/services/season_orchestrator.py`:

```python
from sqlalchemy.orm import Session

from backend.models.season_run import CorpsSeasonPhase, SeasonEventStatus, SeasonRun, SeasonRunStatus
from backend.services.season_phases.critique_learning import process_show_critique
from backend.services.season_phases.offseason import run_offseason_training
from backend.services.season_phases.show_day import run_show_day_rehearsal
from backend.services.season_phases.winter_camps import run_winter_camps


def run_next_season_step(db: Session, *, season_run_id: str) -> SeasonRun:
    run = db.get(SeasonRun, season_run_id)
    if run is None:
        raise ValueError("Season run does not exist.")
    return run


def run_full_season_dry_run(db: Session, *, season_run_id: str) -> SeasonRun:
    run = db.get(SeasonRun, season_run_id)
    if run is None:
        raise ValueError("Season run does not exist.")

    run.status = SeasonRunStatus.OFFSEASON
    for state in run.corps_states:
        run_offseason_training(db, season_run_id=run.id, corps_id=state.corps_id)
        state.phase = CorpsSeasonPhase.WINTER_CAMPS
        run_winter_camps(
            db,
            season_run_id=run.id,
            corps_id=state.corps_id,
            camp_count=run.winter_camp_count,
        )

    run.status = SeasonRunStatus.ON_TOUR
    for event in sorted(run.events, key=lambda item: item.sequence_index):
        event.status = SeasonEventStatus.REHEARSING
        for state in run.corps_states:
            event_state = run_show_day_rehearsal(
                db,
                season_run_id=run.id,
                season_event_id=event.id,
                corps_id=state.corps_id,
            )
            event_state.phase = event_state.phase

        event.status = SeasonEventStatus.CLOSED

    for state in run.corps_states:
        state.phase = CorpsSeasonPhase.SEASON_COMPLETE

    run.status = SeasonRunStatus.COMPLETE
    db.commit()
    db.refresh(run)
    return run
```

- [ ] **Step 4: Replace dry-run placeholders with real phase calls**

Extend the orchestrator so each event calls:

```python
run_show_day_rehearsal(...)
record_competition_result(...)
process_show_critique(...)
```

The final implementation must create scores, tapes, critique adjustments, and event states for every corps at every event.

- [ ] **Step 5: Run full orchestrator test**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_season_orchestrator.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/services/season_orchestrator.py backend/api/v1/seasons.py backend/tests/test_season_orchestrator.py
git commit -m "feat: orchestrate complete multi-show seasons"
```

---

### Task 13: Add Blocked Path Tests and Dashboard Summary API

**Files:**
- Modify: `backend/services/season_orchestrator.py`
- Modify: `backend/api/v1/seasons.py`
- Create: `backend/schemas/season_run.py`
- Test: `backend/tests/test_season_blocked_paths.py`

**Interfaces:**
- Produces:
  - `POST /api/v1/seasons/runs`
  - `GET /api/v1/seasons/runs/{season_run_id}/summary`
  - Response includes season status, current event, corps phases, blockers, next action, scores, tapes, critique adjustments, performer learning.

- [ ] **Step 1: Write failing blocked path test**

Create `backend/tests/test_season_blocked_paths.py`:

```python
from backend.models.season_run import CorpsSeasonPhase, SeasonRunStatus
from backend.services.season_orchestrator import run_full_season_dry_run


def test_season_blocks_when_corps_has_unroutable_segments(db_session, corps_factory, season_calendar_factory, show_factory, segment_factory):
    corps = corps_factory()
    show = show_factory()
    corps.show_id = show.id
    segment_factory(show_id=show.id, caption=None, assigned_role=None)
    run = season_calendar_factory(corps_ids=[corps.id], regular_show_count=1)

    result = run_full_season_dry_run(db_session, season_run_id=run.id)

    assert result.status == SeasonRunStatus.BLOCKED
    state = result.corps_states[0]
    assert state.phase == CorpsSeasonPhase.BLOCKED
    assert "segments without captions" in state.blocker_reason
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_season_blocked_paths.py -q
```

Expected: FAIL until orchestrator checks invariants.

- [ ] **Step 3: Wire invariants into orchestrator**

Modify `run_full_season_dry_run` before winter camps and before each competition:

```python
from backend.services.season_invariants import check_corps_ready_for_tour

blockers = check_corps_ready_for_tour(db, corps_id=state.corps_id)
if blockers:
    state.phase = CorpsSeasonPhase.BLOCKED
    state.blocker_reason = "; ".join(blocker.message for blocker in blockers)
    run.status = SeasonRunStatus.BLOCKED
    run.blocker_reason = state.blocker_reason
    db.commit()
    return run
```

- [ ] **Step 4: Add summary endpoint**

Add a schema in `backend/schemas/season_run.py`:

```python
from pydantic import BaseModel


class CorpsSeasonSummary(BaseModel):
    corps_id: str
    phase: str
    blocker_reason: str | None
    next_action: str


class SeasonRunSummary(BaseModel):
    season_run_id: str
    status: str
    regular_show_count: int
    winter_camp_count: int
    current_event_index: int
    blocker_reason: str | None
    corps: list[CorpsSeasonSummary]


class CreateSeasonRunRequest(BaseModel):
    name: str
    regular_show_count: int
    winter_camp_count: int
    corps_ids: list[str]
```

Add endpoint in `backend/api/v1/seasons.py`:

```python
@router.post("/runs", response_model=SeasonRunSummary)
def create_season_run(payload: CreateSeasonRunRequest, db: Session = Depends(get_db)):
    if payload.regular_show_count < 1:
        raise HTTPException(status_code=422, detail="regular_show_count must be at least 1")
    if payload.winter_camp_count < 1 or payload.winter_camp_count > 7:
        raise HTTPException(status_code=422, detail="winter_camp_count must be between 1 and 7")
    run = create_season_calendar(
        db,
        name=payload.name,
        regular_show_count=payload.regular_show_count,
        winter_camp_count=payload.winter_camp_count,
        corps_ids=payload.corps_ids,
    )
    return _season_run_summary(run)


@router.get("/runs/{season_run_id}/summary", response_model=SeasonRunSummary)
def get_season_run_summary(season_run_id: str, db: Session = Depends(get_db)):
    run = db.get(SeasonRun, season_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Season run not found")
    return _season_run_summary(run)


def _season_run_summary(run: SeasonRun) -> SeasonRunSummary:
    return SeasonRunSummary(
        season_run_id=run.id,
        status=run.status.value,
        regular_show_count=run.regular_show_count,
        winter_camp_count=run.winter_camp_count,
        current_event_index=run.current_event_index,
        blocker_reason=run.blocker_reason,
        corps=[
            CorpsSeasonSummary(
                corps_id=state.corps_id,
                phase=state.phase.value,
                blocker_reason=state.blocker_reason,
                next_action=_next_action_for_phase(state.phase, state.blocker_reason),
            )
            for state in run.corps_states
        ],
    )
```

- [ ] **Step 5: Run blocked path and API tests**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_season_blocked_paths.py backend/tests/test_seasons_api.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/services/season_orchestrator.py backend/api/v1/seasons.py backend/schemas/season_run.py backend/tests/test_season_blocked_paths.py
git commit -m "feat: expose season blockers and next actions"
```

---

### Task 14: Make the UI Show the Actual Season Machine

**Files:**
- Modify: `frontend/src/pages/Seasons.tsx`
- Modify: `frontend/src/pages/CorpsDetail.tsx`
- Modify: `frontend/src/pages/StaffMarketplace.tsx`
- Create: `frontend/src/components/season/SeasonRunSettings.tsx`
- Create: `frontend/src/components/season/SeasonRunTimeline.tsx`
- Create: `frontend/src/components/season/CorpsSeasonPanel.tsx`
- Create: `frontend/src/components/season/EventCritiquePanel.tsx`
- Modify: `frontend/src/services/api.ts`
- Test: existing frontend test location or create `frontend/src/components/season/__tests__/SeasonRunTimeline.test.tsx`

**Interfaces:**
- Consumes:
  - `GET /api/v1/seasons/runs/{season_run_id}/summary`
- Produces:
  - A season settings control for regular-season show count and winter camp count.
  - A season timeline with configured regular shows and finals.
  - Per-corps phase cards showing staff, performers, next action, blocker, latest score, latest tape, latest critique adjustment.
  - Staff marketplace actions for hire, fire, and train.

- [ ] **Step 1: Add API client function**

Modify `frontend/src/services/api.ts`:

```ts
export interface CorpsSeasonSummary {
  corps_id: string;
  phase: string;
  blocker_reason: string | null;
  next_action: string;
}

export interface SeasonRunSummary {
  season_run_id: string;
  status: string;
  regular_show_count: number;
  winter_camp_count: number;
  current_event_index: number;
  blocker_reason: string | null;
  corps: CorpsSeasonSummary[];
}

export async function getSeasonRunSummary(seasonRunId: string): Promise<SeasonRunSummary> {
  const response = await fetch(`/api/v1/seasons/runs/${seasonRunId}/summary`);
  if (!response.ok) {
    throw new Error(`Failed to load season run summary: ${response.status}`);
  }
  return response.json();
}

export interface CreateSeasonRunRequest {
  name: string;
  regular_show_count: number;
  winter_camp_count: number;
  corps_ids: string[];
}

export async function createSeasonRun(payload: CreateSeasonRunRequest): Promise<SeasonRunSummary> {
  if (payload.winter_camp_count < 1 || payload.winter_camp_count > 7) {
    throw new Error("winter_camp_count must be between 1 and 7");
  }
  const response = await fetch("/api/v1/seasons/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Failed to create season run: ${response.status}`);
  }
  return response.json();
}
```

- [ ] **Step 2: Create season settings component**

Create `frontend/src/components/season/SeasonRunSettings.tsx`:

```tsx
interface Props {
  regularShowCount: number;
  winterCampCount: number;
  onRegularShowCountChange: (value: number) => void;
  onWinterCampCountChange: (value: number) => void;
}

export function SeasonRunSettings({
  regularShowCount,
  winterCampCount,
  onRegularShowCountChange,
  onWinterCampCountChange,
}: Props) {
  return (
    <section className="season-run-settings">
      <label>
        Regular shows
        <input
          type="number"
          min={1}
          value={regularShowCount}
          onChange={(event) => onRegularShowCountChange(Number(event.target.value))}
        />
      </label>
      <label>
        Winter camps
        <input
          type="number"
          min={1}
          max={7}
          value={winterCampCount}
          onChange={(event) => onWinterCampCountChange(Number(event.target.value))}
        />
      </label>
    </section>
  );
}
```

- [ ] **Step 3: Create season timeline component**

Create `frontend/src/components/season/SeasonRunTimeline.tsx`:

```tsx
import type { SeasonRunSummary } from "../../services/api";

interface Props {
  summary: SeasonRunSummary;
}

export function SeasonRunTimeline({ summary }: Props) {
  return (
    <section className="season-run-timeline">
      <header>
        <h2>Season Run</h2>
        <span>{summary.status}</span>
      </header>
      <p>
        {summary.regular_show_count} regular shows, finals, {summary.winter_camp_count} winter camps
      </p>
      {summary.blocker_reason ? (
        <p className="season-blocker">{summary.blocker_reason}</p>
      ) : null}
      <ol>
        {summary.corps.map((corps) => (
          <li key={corps.corps_id}>
            <strong>{corps.corps_id}</strong>
            <span>{corps.phase}</span>
            <span>{corps.next_action}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
```

- [ ] **Step 4: Add corps season panel**

Create `frontend/src/components/season/CorpsSeasonPanel.tsx`:

```tsx
import type { CorpsSeasonSummary } from "../../services/api";

interface Props {
  corps: CorpsSeasonSummary;
}

export function CorpsSeasonPanel({ corps }: Props) {
  return (
    <article className="corps-season-panel">
      <header>
        <h3>{corps.corps_id}</h3>
        <span>{corps.phase}</span>
      </header>
      <p>{corps.next_action}</p>
      {corps.blocker_reason ? <p className="blocker">{corps.blocker_reason}</p> : null}
    </article>
  );
}
```

- [ ] **Step 5: Wire pages**

Update `Seasons.tsx` to load the selected run summary and render `SeasonRunTimeline`.

Update the season creation form in `Seasons.tsx` to render `SeasonRunSettings` with:

```tsx
<SeasonRunSettings
  regularShowCount={regularShowCount}
  winterCampCount={winterCampCount}
  onRegularShowCountChange={setRegularShowCount}
  onWinterCampCountChange={setWinterCampCount}
/>
```

Validate in the submit handler:

```tsx
if (winterCampCount < 1 || winterCampCount > 7) {
  setFormError("Winter camps must be between 1 and 7.");
  return;
}
```

Update `CorpsDetail.tsx` to show:

```tsx
<CorpsSeasonPanel corps={selectedCorpsSeasonSummary} />
```

Update `StaffMarketplace.tsx` so marketplace rows expose explicit hire/train/fire actions using existing staff endpoints.

- [ ] **Step 6: Add frontend test**

Create `frontend/src/components/season/__tests__/SeasonRunTimeline.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { SeasonRunTimeline } from "../SeasonRunTimeline";

test("renders season status, corps phase, next action, and blocker", () => {
  render(
    <SeasonRunTimeline
      summary={{
        season_run_id: "season-1",
        status: "blocked",
        regular_show_count: 4,
        winter_camp_count: 7,
        current_event_index: 1,
        blocker_reason: "Corps show has segments without captions.",
        corps: [
          {
            corps_id: "corps-1",
            phase: "blocked",
            blocker_reason: "Corps show has segments without captions.",
            next_action: "Fix unroutable segments.",
          },
        ],
      }}
    />
  );

  expect(screen.getByText("blocked")).toBeInTheDocument();
  expect(screen.getByText("4 regular shows, finals, 7 winter camps")).toBeInTheDocument();
  expect(screen.getByText("corps-1")).toBeInTheDocument();
  expect(screen.getByText("Fix unroutable segments.")).toBeInTheDocument();
  expect(screen.getByText("Corps show has segments without captions.")).toBeInTheDocument();
});
```

- [ ] **Step 7: Run frontend tests**

Run:

```bash
npm test -- SeasonRunTimeline
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/Seasons.tsx frontend/src/pages/CorpsDetail.tsx frontend/src/pages/StaffMarketplace.tsx frontend/src/components/season frontend/src/services/api.ts
git commit -m "feat: show authoritative season lifecycle in UI"
```

---

### Task 15: Runtime Reliability Pass

**Files:**
- Modify: `backend/database.py`
- Modify: `backend/services/runtime_config.py`
- Modify: `backend/services/metronome_heartbeat.py`
- Modify: `backend/services/task_manager.py`
- Test: `backend/tests/test_runtime_db_config.py`

**Interfaces:**
- Produces:
  - Single configured DB URL source.
  - SQLite WAL and busy timeout when SQLite is used.
  - Health check warning when multiple local DB files exist.
  - Metronome schema compatibility with current models.

- [ ] **Step 1: Write failing DB config test**

Create `backend/tests/test_runtime_db_config.py`:

```python
from backend.services.runtime_config import resolve_database_url


def test_database_url_resolves_from_single_source(monkeypatch):
    monkeypatch.setenv("DCI_DATABASE_URL", "sqlite:///tmp/test.db")

    assert resolve_database_url() == "sqlite:///tmp/test.db"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_runtime_db_config.py -q
```

Expected: FAIL until `resolve_database_url` is centralized.

- [ ] **Step 3: Implement DB URL resolver**

Add to `backend/services/runtime_config.py`:

```python
import os


def resolve_database_url() -> str:
    return os.environ.get("DCI_DATABASE_URL", "sqlite:///./dci_swarm.db")
```

Modify `backend/database.py` to call `resolve_database_url()`.

- [ ] **Step 4: Add SQLite connection pragmas**

In `backend/database.py`, add SQLite connect listener:

```python
from sqlalchemy import event


if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()
```

- [ ] **Step 5: Fix metronome stale schema assumptions**

Search:

```bash
rg "updated_at|Segment\\.corps_id|SessionLocal" backend/services logs/metronome -n
```

Replace metronome reads of missing columns with current model fields or helper services. Add tests for any helper functions used to identify stalled sessions.

- [ ] **Step 6: Run reliability tests**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_runtime_db_config.py backend/tests/test_system_health.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/database.py backend/services/runtime_config.py backend/services/metronome_heartbeat.py backend/services/task_manager.py backend/tests/test_runtime_db_config.py
git commit -m "fix: stabilize runtime database configuration"
```

---

## Verification Sequence

After all tasks:

```bash
.venv/bin/python -m pytest backend/tests/test_season_run_models.py \
  backend/tests/test_season_calendar.py \
  backend/tests/test_season_invariants.py \
  backend/tests/test_offseason_phase.py \
  backend/tests/test_season_design_phase.py \
  backend/tests/test_recruiting_phase.py \
  backend/tests/test_winter_camps_phase.py \
  backend/tests/test_show_day_phase.py \
  backend/tests/test_mission_packets.py \
  backend/tests/test_competition_product_links.py \
  backend/tests/test_critique_learning_phase.py \
  backend/tests/test_season_orchestrator.py \
  backend/tests/test_season_blocked_paths.py \
  backend/tests/test_runtime_db_config.py -q
```

Expected: all listed tests PASS.

Then run the existing target regression slice:

```bash
.venv/bin/python -m pytest backend/tests/test_rep.py backend/tests/test_verification.py backend/tests/test_verification_gates.py backend/tests/test_show.py backend/tests/test_show_persistence.py backend/tests/test_season_persistence.py backend/tests/test_system_health.py backend/tests/test_metrics_aggregation.py -q
```

Expected: PASS. The last audited baseline was `120 passed in 7.09s`.

Frontend:

```bash
npm test -- SeasonRunTimeline
```

Expected: PASS.

Manual smoke:

```bash
.venv/bin/python -m pytest backend/tests/test_season_orchestrator.py::test_full_season_runs_multiple_shows_finals_and_evolution -q
```

Expected: PASS and creates:

- One season run.
- `N` regular shows plus finals.
- Rehearsal blocks for each corps and event.
- Mission packets for each dispatched agent session.
- Scores linked to products.
- Tapes linked to products.
- Critique adjustments linked to tapes.
- Corps season states marked complete.
- Performer learning deltas recorded.

## Self-Review

Spec coverage:

- Staff hiring/firing/training is covered by Task 13 UI work and should reuse existing staff endpoints; deeper backend staff lifecycle can be split into a follow-up if endpoints are incomplete.
- Offseason member improvement is covered by Task 4.
- Show design cycle is covered by Task 5.
- Recruiting with prestige/cachet mechanics is covered by Task 6.
- Winter camps are covered by Task 7.
- Repeated tour shows are covered by Tasks 8 and 11.
- Basics, visual, music, sectionals, ensemble, and run-through are covered by Task 8.
- Narrow agent missions and out-of-scope blocking are covered by Task 9.
- Competition, scores, and tapes are covered by Task 10.
- Staff reaction, critique, and adjusted plans are covered by Task 11.
- Finals and season completion are covered by Task 12.
- Blockers and comprehensible interface are covered by Tasks 13 and 14.
- Runtime failure causes from the audit are covered by Task 15.

Known follow-up after this plan:

- Replace dry-run scoring with real model-vs-model comparison scenarios for the local LLM testbed.
- Add explicit corps strategy mutation proposals driven by critique adjustments.
- Add finals-only awards, caption trophies, and item selection/crowning mechanics.
- Add a migration plan if the project uses Alembic revision files rather than `Base.metadata.create_all` in tests.
