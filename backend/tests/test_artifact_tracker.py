"""Tests for artifact tracker and performance records."""

import json

import pytest
from sqlalchemy import text

from backend.models.artifact import Artifact, ArtifactType
from backend.models.performance_record import PerformanceRecord
from backend.services.artifact_tracker import (
    record_artifact,
    record_performance,
    record_standings,
    get_corps_artifacts,
    get_corps_performance_history,
)


@pytest.fixture(autouse=True)
def _create_tables(db):
    """Ensure artifact and performance_record tables exist."""
    from backend.database import Base
    Base.metadata.create_all(bind=db.get_bind())
    yield


class TestRecordArtifact:
    def test_basic_artifact(self, db):
        art = record_artifact(
            db,
            "generated_images/logo_test.png",
            ArtifactType.LOGO,
            label="Test logo",
        )
        assert art.id
        assert art.artifact_type == ArtifactType.LOGO
        assert art.file_path == "generated_images/logo_test.png"
        assert art.label == "Test logo"

    def test_artifact_with_context(self, db):
        art = record_artifact(
            db,
            "seasons/s1/post_mortems/c1.md",
            ArtifactType.POST_MORTEM,
            corps_id="test-corps-1",
            season_id="s1",
        )
        assert art.corps_id == "test-corps-1"
        assert art.season_id == "s1"

    def test_get_corps_artifacts(self, db):
        record_artifact(db, "file1.png", ArtifactType.LOGO, corps_id="c1")
        record_artifact(db, "file2.md", ArtifactType.POST_MORTEM, corps_id="c1")
        record_artifact(db, "file3.png", ArtifactType.LOGO, corps_id="c2")

        arts = get_corps_artifacts(db, "c1")
        assert len(arts) == 2
        assert all(a["corps_id"] == "c1" for a in arts)


class TestRecordPerformance:
    def test_basic_performance(self, db):
        rec = record_performance(
            db,
            corps_id="c1",
            season_id="s1",
            competition_id="s1-round-1",
            show_slug="test-show",
            round_number=1,
            placement=2,
            field_size=5,
            final_score=75.5,
            raw_score=75.5,
            caption_scores={"brass": 80, "percussion": 70},
        )
        assert rec.id
        assert rec.placement == 2
        assert rec.final_score == 75.5
        assert rec.corps_name == "c1"  # fallback since no Corps in DB

    def test_deduplication(self, db):
        kwargs = dict(
            corps_id="c1",
            season_id="s1",
            competition_id="s1-round-1",
            show_slug="test-show",
            round_number=1,
            placement=1,
            field_size=3,
            final_score=80.0,
            raw_score=80.0,
            caption_scores={},
        )
        rec1 = record_performance(db, **kwargs)
        rec2 = record_performance(db, **kwargs)
        assert rec1.id == rec2.id  # Same record returned

    def test_get_performance_history(self, db):
        for i in range(3):
            record_performance(
                db,
                corps_id="c1",
                season_id="s1",
                competition_id=f"s1-round-{i+1}",
                show_slug=f"show-{i+1}",
                round_number=i + 1,
                placement=i + 1,
                field_size=5,
                final_score=80.0 - i * 5,
                raw_score=80.0 - i * 5,
                caption_scores={"brass": 80},
            )

        history = get_corps_performance_history(db, "c1")
        assert len(history) == 3


class TestRecordStandings:
    def test_records_all_standings(self, db):
        standings = [
            {"corps_id": "c1", "rank": 1, "final_score": 85.0, "raw_score": 85.0, "caption_scores": {"brass": 90}},
            {"corps_id": "c2", "rank": 2, "final_score": 72.0, "raw_score": 72.0, "caption_scores": {"brass": 70}},
            {"corps_id": "c3", "rank": 3, "final_score": 60.0, "raw_score": 60.0, "caption_scores": {"brass": 55}},
        ]
        records = record_standings(
            db,
            season_id="s1",
            competition_id="s1-round-1",
            show_slug="test-show",
            round_number=1,
            standings=standings,
            completed_at="2026-02-14T10:00:00+00:00",
        )
        assert len(records) == 3
        assert records[0].placement == 1
        assert records[0].final_score == 85.0
        assert records[2].placement == 3

    def test_caption_scores_serialized_as_json(self, db):
        standings = [
            {"corps_id": "c1", "rank": 1, "final_score": 85.0, "raw_score": 85.0,
             "caption_scores": {"brass": 90, "percussion": 80}},
        ]
        records = record_standings(db, "s1", "s1-round-1", "show", 1, standings)
        rec = records[0]
        parsed = json.loads(rec.caption_scores_json)
        assert parsed["brass"] == 90
        assert parsed["percussion"] == 80


class TestPerformanceRecordToDict:
    def test_to_dict(self, db):
        rec = record_performance(
            db,
            corps_id="c1",
            season_id="s1",
            competition_id="s1-round-1",
            show_slug="show-1",
            round_number=1,
            placement=1,
            field_size=5,
            final_score=85.5,
            raw_score=85.5,
            caption_scores={"brass": 90, "guard": 80},
        )
        d = rec.to_dict()
        assert d["corps_id"] == "c1"
        assert d["final_score"] == 85.5
        assert d["caption_scores"]["brass"] == 90
        assert d["round_number"] == 1
