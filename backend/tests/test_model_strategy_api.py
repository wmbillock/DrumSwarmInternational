"""Tests for model strategy V1 API routes."""

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
import backend.models  # noqa: F401


@pytest.fixture
def project_root(tmp_path, monkeypatch):
    monkeypatch.setenv("DCI_PROJECT_ROOT", str(tmp_path))
    (tmp_path / "shows").mkdir()
    (tmp_path / "corps").mkdir()
    (tmp_path / "seasons").mkdir()
    return tmp_path


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def client(project_root, engine, monkeypatch):
    TestSessionFactory = sessionmaker(bind=engine)
    monkeypatch.setattr("backend.api.app.SessionFactory", TestSessionFactory)
    from backend.api.app import app
    return TestClient(app)


@pytest.fixture
def db_session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def _seed_corps(db, corps_id="test-corps", name="Test Corps", color_scheme=None):
    from backend.models.corps import Corps
    corps = Corps(id=corps_id, name=name, color_scheme=color_scheme)
    db.add(corps)
    db.commit()
    return corps_id


def _seed_strategy(db, corps_id, policy="best_of_breed", provider=None,
                   risk=0.5, exploration=0.1):
    from backend.models.corps_strategy import CorpsStrategy
    strategy = CorpsStrategy(
        corps_id=corps_id,
        model_policy=policy,
        preferred_provider=provider,
        risk_tolerance=risk,
        exploration_rate=exploration,
        adaptation_style="model_swap",
    )
    db.add(strategy)
    db.commit()
    return strategy


def _seed_spec(db, name="test-spec", provider="anthropic",
               model_id="claude-sonnet-4-5", categories="frontend,backend"):
    from backend.models.model_spec import ModelSpec
    spec = ModelSpec(
        name=name, provider=provider, model_id=model_id,
        task_categories=categories,
    )
    db.add(spec)
    db.commit()
    return spec


def _seed_performance(db, spec_id, category, score, attempts=5, corps_id=None):
    from backend.services.model_spec_service import record_model_spec_outcome
    for _ in range(attempts):
        record_model_spec_outcome(db, spec_id, category, score=score,
                                  success=True, corps_id=corps_id)
    db.commit()


class TestGetStrategyForCorps:
    def test_get_strategy_for_corps(self, client, db_session):
        """GET /corps/{id}/strategy returns strategy config + performance."""
        cid = _seed_corps(db_session, "strat-corps", "Strategy Corps")
        _seed_strategy(db_session, cid, policy="best_of_breed", exploration=0.2)

        spec = _seed_spec(db_session, "spec-a", categories="frontend")
        _seed_performance(db_session, spec.id, "frontend", 85.0, corps_id=cid)

        r = client.get(f"/api/v1/corps/{cid}/strategy")
        assert r.status_code == 200
        data = r.json()

        assert data["corps_id"] == cid
        assert data["corps_name"] == "Strategy Corps"
        assert data["strategy"]["model_policy"] == "best_of_breed"
        assert data["strategy"]["exploration_rate"] == pytest.approx(0.2)
        assert "frontend" in data["performance"]
        assert data["performance"]["frontend"]["avg_score"] == pytest.approx(85.0)

    def test_get_strategy_not_found(self, client, db_session):
        """GET /corps/{id}/strategy returns 404 when corps has no strategy."""
        _seed_corps(db_session, "no-strat", "No Strategy")
        r = client.get("/api/v1/corps/no-strat/strategy")
        assert r.status_code == 404

    def test_get_strategy_corps_not_found(self, client):
        """GET /corps/{id}/strategy returns 404 for nonexistent corps."""
        r = client.get("/api/v1/corps/nonexistent/strategy")
        assert r.status_code == 404


class TestLeaderboardEndpoint:
    def test_leaderboard_endpoint(self, client, db_session):
        """GET /leaderboard/{category} returns ranked specs."""
        spec_a = _seed_spec(db_session, "fast-model", provider="anthropic",
                            categories="backend")
        spec_b = _seed_spec(db_session, "slow-model", provider="ollama",
                            model_id="deepseek-v2", categories="backend")

        _seed_performance(db_session, spec_a.id, "backend", 90.0)
        _seed_performance(db_session, spec_b.id, "backend", 70.0)

        r = client.get("/api/v1/leaderboard/backend")
        assert r.status_code == 200
        data = r.json()

        assert data["task_category"] == "backend"
        assert len(data["entries"]) == 2
        # First entry should be higher score
        assert data["entries"][0]["avg_score"] > data["entries"][1]["avg_score"]
        assert data["entries"][0]["name"] == "fast-model"

    def test_leaderboard_empty(self, client):
        """GET /leaderboard/{category} returns empty for unknown category."""
        r = client.get("/api/v1/leaderboard/nonexistent")
        assert r.status_code == 200
        assert r.json()["entries"] == []


class TestUpdateStrategyManually:
    def test_update_strategy_manually(self, client, db_session):
        """PUT /corps/{id}/strategy updates strategy fields."""
        cid = _seed_corps(db_session, "update-corps", "Update Corps")
        _seed_strategy(db_session, cid, policy="single_provider",
                       provider="anthropic", exploration=0.05)

        r = client.put(f"/api/v1/corps/{cid}/strategy", json={
            "model_policy": "best_of_breed",
            "exploration_rate": 0.3,
        })
        assert r.status_code == 200
        data = r.json()

        assert data["corps_id"] == cid
        assert "model_policy" in data["updated_fields"]
        assert "exploration_rate" in data["updated_fields"]
        assert data["strategy"]["model_policy"] == "best_of_breed"
        assert data["strategy"]["exploration_rate"] == pytest.approx(0.3)

    def test_update_strategy_invalid_fields_only(self, client, db_session):
        """PUT /corps/{id}/strategy with only invalid fields returns 400."""
        cid = _seed_corps(db_session, "bad-update", "Bad Update")
        _seed_strategy(db_session, cid)

        r = client.put(f"/api/v1/corps/{cid}/strategy", json={
            "invalid_field": "value",
        })
        assert r.status_code == 400

    def test_update_strategy_section_overrides_as_dict(self, client, db_session):
        """PUT /corps/{id}/strategy accepts section_overrides as dict."""
        cid = _seed_corps(db_session, "override-corps", "Override Corps")
        _seed_strategy(db_session, cid, policy="section_specialized")

        spec = _seed_spec(db_session, "override-spec")
        r = client.put(f"/api/v1/corps/{cid}/strategy", json={
            "section_overrides": {"frontend": spec.id},
        })
        assert r.status_code == 200
        assert r.json()["strategy"]["section_overrides"]["frontend"] == spec.id


class TestStrategyInheritsCorpsTheme:
    def test_strategy_inherits_corps_theme(self, client, db_session):
        """GET /corps/{id}/strategy includes the corps color_scheme."""
        colors = json.dumps({
            "primary": "#1a2b3c",
            "secondary": "#4d5e6f",
            "accent": "#ff9900",
        })
        cid = _seed_corps(db_session, "themed-corps", "Themed Corps",
                          color_scheme=colors)
        _seed_strategy(db_session, cid)

        r = client.get(f"/api/v1/corps/{cid}/strategy")
        assert r.status_code == 200
        data = r.json()

        assert data["color_scheme"]["primary"] == "#1a2b3c"
        assert data["color_scheme"]["secondary"] == "#4d5e6f"
        assert data["color_scheme"]["accent"] == "#ff9900"

    def test_strategy_no_theme_returns_empty(self, client, db_session):
        """GET /corps/{id}/strategy returns empty color_scheme when none set."""
        cid = _seed_corps(db_session, "plain-corps", "Plain Corps")
        _seed_strategy(db_session, cid)

        r = client.get(f"/api/v1/corps/{cid}/strategy")
        assert r.status_code == 200
        assert r.json()["color_scheme"] == {}


class TestModelSpecsEndpoint:
    def test_list_model_specs(self, client, db_session):
        """GET /model-specs returns all specs with performance."""
        spec = _seed_spec(db_session, "listed-spec", categories="frontend")
        _seed_performance(db_session, spec.id, "frontend", 88.0)

        r = client.get("/api/v1/model-specs")
        assert r.status_code == 200
        data = r.json()

        assert len(data) >= 1
        found = [s for s in data if s["id"] == spec.id]
        assert len(found) == 1
        assert found[0]["name"] == "listed-spec"
        assert "frontend" in found[0]["performance"]

    def test_get_spec_performance(self, client, db_session):
        """GET /model-specs/{id}/performance returns breakdown."""
        spec = _seed_spec(db_session, "perf-spec", categories="backend")
        _seed_performance(db_session, spec.id, "backend", 75.0)
        cid = _seed_corps(db_session, "perf-corps", "Perf Corps")
        _seed_performance(db_session, spec.id, "backend", 80.0, corps_id=cid)

        r = client.get(f"/api/v1/model-specs/{spec.id}/performance")
        assert r.status_code == 200
        data = r.json()

        assert data["spec_id"] == spec.id
        assert len(data["global"]) == 1
        assert data["global"][0]["task_category"] == "backend"
        assert len(data["by_corps"]) == 1
        assert data["by_corps"][0]["corps_id"] == cid

    def test_get_spec_performance_not_found(self, client):
        """GET /model-specs/{id}/performance returns 404 for unknown spec."""
        r = client.get("/api/v1/model-specs/nonexistent/performance")
        assert r.status_code == 404
