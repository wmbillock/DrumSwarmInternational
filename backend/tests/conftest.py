import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database import Base

# Import all models so Base.metadata.create_all picks them up
import backend.models  # noqa: F401


@pytest.fixture(scope="session", autouse=True)
def _set_test_mode():
    """Set DCI_TEST_MODE for the entire test session.

    This causes the FastAPI lifespan to:
    - Skip seed_founding_corps()
    - Force MockLLMClient (skip build_llm_client() provider detection)
    - Skip start_metronome()
    - Skip event bus subscriptions that require WebSocket
    """
    os.environ["DCI_TEST_MODE"] = "1"
    yield
    os.environ.pop("DCI_TEST_MODE", None)


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
def client():
    """Create a TestClient with in-memory DB and test-mode lifespan.

    Monkeypatches the app-level engine + SessionFactory so the lifespan
    (and any endpoint that calls get_db()) uses in-memory SQLite.
    """
    from unittest.mock import patch
    from fastapi.testclient import TestClient

    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)
    test_session_factory = sessionmaker(bind=test_engine)

    with patch("backend.api.app.engine", test_engine), \
         patch("backend.api.app.SessionFactory", test_session_factory):
        from backend.api.app import app
        with TestClient(app) as tc:
            yield tc
