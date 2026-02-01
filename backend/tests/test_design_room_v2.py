"""Tests for Design Room v2 endpoints — prompt, lint, publish."""

import os
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient backed by tmp_path as project root."""
    monkeypatch.setenv("DCI_PROJECT_ROOT", str(tmp_path))
    (tmp_path / "shows").mkdir()
    from backend.api.v1.router import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _create_thread(client, title="Test Show"):
    resp = client.post("/api/v1/design/threads", json={"title": title})
    assert resp.status_code == 200
    return resp.json()["slug"]


FULL_PROMPT = """# Test Show

## Show Concept
A dramatic exploration of light and shadow with full brass scoring.

## Musical Design
Opening fanfare in Bb major, transitions through relative minor keys.

## Visual Design
Geometric formations with LED props creating shadow patterns on field.

## Guard Design
Silk flags in gradient colors, rifle feature in movement three.

## General Effect
Audience experiences journey from darkness to illumination across show arc.

## Constraints
- Must complete within 11-minute time limit
- All props must be field-legal per DCI rules
- Maximum 150 performers on field

## Deliverables
- Full musical score for brass, percussion, and front ensemble
- Drill charts for all movements
- Guard choreography notation

## Evaluation Rubric
Brass clarity and intonation weighted at 30%, visual design and spacing at 25%.
"""


class TestUpdatePrompt:
    def test_put_prompt_writes_file(self, client, tmp_path):
        slug = _create_thread(client)
        resp = client.put(
            f"/api/v1/design/threads/{slug}/artifacts/prompt",
            json={"content": "# My Prompt\n"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"
        assert (tmp_path / "shows" / slug / "show_prompt.md").read_text() == "# My Prompt\n"

    def test_put_prompt_404_missing_thread(self, client):
        resp = client.put(
            "/api/v1/design/threads/nonexistent/artifacts/prompt",
            json={"content": "x"},
        )
        assert resp.status_code == 404


class TestLintPrompt:
    def test_lint_returns_correct_structure(self, client):
        slug = _create_thread(client)
        resp = client.post(f"/api/v1/design/threads/{slug}/lint")
        assert resp.status_code == 200
        data = resp.json()
        assert "required_fix" in data
        assert "nice_to_have" in data
        assert "acceptable_risk" in data

    def test_lint_empty_prompt_has_required_fixes(self, client):
        slug = _create_thread(client)
        resp = client.post(f"/api/v1/design/threads/{slug}/lint")
        data = resp.json()
        # Empty prompt should have missing section findings
        assert len(data["required_fix"]) > 0

    def test_lint_full_prompt_clean(self, client):
        slug = _create_thread(client)
        client.put(
            f"/api/v1/design/threads/{slug}/artifacts/prompt",
            json={"content": FULL_PROMPT},
        )
        resp = client.post(f"/api/v1/design/threads/{slug}/lint")
        data = resp.json()
        assert len(data["required_fix"]) == 0


class TestPublishThread:
    def test_publish_succeeds_when_approved_and_lint_clean(self, client, tmp_path):
        slug = _create_thread(client)
        # Write full prompt
        client.put(
            f"/api/v1/design/threads/{slug}/artifacts/prompt",
            json={"content": FULL_PROMPT},
        )
        # Approve the thread (needs spec content first)
        client.put(
            f"/api/v1/design/threads/{slug}/artifacts/brief",
            json={"content": "# Spec\nsome content"},
        )
        client.post(f"/api/v1/design/threads/{slug}/approve")
        # Now publish
        resp = client.post(f"/api/v1/design/threads/{slug}/publish")
        assert resp.status_code == 200
        assert resp.json()["status"] == "published"
        # Verify status on disk
        status = yaml.safe_load((tmp_path / "shows" / slug / "status.yaml").read_text())
        assert status["status"] == "published"

    def test_publish_rejects_when_draft(self, client):
        slug = _create_thread(client)
        resp = client.post(f"/api/v1/design/threads/{slug}/publish")
        assert resp.status_code == 400
        assert "approved" in resp.json()["detail"].lower()

    def test_publish_rejects_when_lint_has_required_fixes(self, client):
        slug = _create_thread(client)
        # Approve with spec but leave prompt empty (lint will fail)
        client.put(
            f"/api/v1/design/threads/{slug}/artifacts/brief",
            json={"content": "# Spec\ncontent"},
        )
        client.post(f"/api/v1/design/threads/{slug}/approve")
        resp = client.post(f"/api/v1/design/threads/{slug}/publish")
        assert resp.status_code == 400
        assert "required fixes" in resp.json()["detail"].lower()
