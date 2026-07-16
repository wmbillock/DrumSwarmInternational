import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base

# Import all models so Base.metadata.create_all picks them up
import backend.models.segment  # noqa: F401
import backend.models.rep  # noqa: F401
import backend.models.message  # noqa: F401
import backend.models.problem  # noqa: F401
import backend.models.subscription  # noqa: F401
import backend.models.agent_definition  # noqa: F401
import backend.models.agent_session  # noqa: F401
import backend.models.score  # noqa: F401
import backend.models.penalty  # noqa: F401
import backend.models.corps  # noqa: F401
import backend.models.show  # noqa: F401
import backend.models.work_log  # noqa: F401
import backend.models.performer  # noqa: F401
import backend.models.messaging_thread  # noqa: F401
import backend.models.season_run  # noqa: F401
import backend.models.rehearsal_block  # noqa: F401
import backend.models.mission_packet  # noqa: F401
import backend.models.judging_tape  # noqa: F401
import backend.models.critique_adjustment  # noqa: F401


# Enable test mode globally — skips lifespan heavy init (LLM, metronome, seeder)
os.environ["DCI_TEST_MODE"] = "1"


@pytest.fixture
def db():
    """Create an in-memory SQLite database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """Shared TestClient fixture with isolated DB and project root.

    Use this instead of creating TestClient(app) directly in test files.
    Sets DCI_TEST_MODE=1 so lifespan skips LLM client + metronome.
    """
    from fastapi.testclient import TestClient
    from backend.api.app import app, get_db

    monkeypatch.setenv("DCI_PROJECT_ROOT", str(tmp_path))
    (tmp_path / "shows").mkdir()
    (tmp_path / "corps").mkdir()
    (tmp_path / "seasons").mkdir()

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("backend.api.app.SessionFactory", TestingSession)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
