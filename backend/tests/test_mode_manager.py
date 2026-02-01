"""Tests for mode_manager service."""

import pytest
from backend.models.corps import Corps, CorpsStatus, CorpsMode
from backend.services.mode_manager import switch_mode, ModeError


def _make_corps(db, mode=None, status=CorpsStatus.WINTER_CAMPS):
    corps = Corps(name="Test Corps", status=status, mode=mode)
    db.add(corps)
    db.commit()
    return corps


class TestSwitchMode:
    def test_switch_from_none_to_design_room(self, db):
        corps = _make_corps(db)
        result = switch_mode(db, corps.id, CorpsMode.DESIGN_ROOM)
        assert result.mode == CorpsMode.DESIGN_ROOM

    def test_switch_from_none_to_rehearsal_mode(self, db):
        corps = _make_corps(db)
        result = switch_mode(db, corps.id, CorpsMode.REHEARSAL_MODE)
        assert result.mode == CorpsMode.REHEARSAL_MODE

    def test_switch_from_none_to_show_mode_invalid(self, db):
        corps = _make_corps(db)
        with pytest.raises(ModeError, match="Cannot transition"):
            switch_mode(db, corps.id, CorpsMode.SHOW_MODE)

    def test_switch_design_room_to_show_mode(self, db):
        corps = _make_corps(db, mode=CorpsMode.DESIGN_ROOM)
        result = switch_mode(db, corps.id, CorpsMode.SHOW_MODE)
        assert result.mode == CorpsMode.SHOW_MODE

    def test_switch_design_room_to_rehearsal_mode(self, db):
        corps = _make_corps(db, mode=CorpsMode.DESIGN_ROOM)
        result = switch_mode(db, corps.id, CorpsMode.REHEARSAL_MODE)
        assert result.mode == CorpsMode.REHEARSAL_MODE

    def test_switch_rehearsal_to_judging(self, db):
        corps = _make_corps(db, mode=CorpsMode.REHEARSAL_MODE)
        result = switch_mode(db, corps.id, CorpsMode.JUDGING)
        assert result.mode == CorpsMode.JUDGING

    def test_switch_judging_to_offseason(self, db):
        corps = _make_corps(db, mode=CorpsMode.JUDGING)
        result = switch_mode(db, corps.id, CorpsMode.OFFSEASON_REVIEW)
        assert result.mode == CorpsMode.OFFSEASON_REVIEW

    def test_switch_offseason_to_design_room(self, db):
        corps = _make_corps(db, mode=CorpsMode.OFFSEASON_REVIEW)
        result = switch_mode(db, corps.id, CorpsMode.DESIGN_ROOM)
        assert result.mode == CorpsMode.DESIGN_ROOM

    def test_switch_offseason_to_show_mode_invalid(self, db):
        corps = _make_corps(db, mode=CorpsMode.OFFSEASON_REVIEW)
        with pytest.raises(ModeError, match="Cannot transition"):
            switch_mode(db, corps.id, CorpsMode.SHOW_MODE)

    def test_switch_disbanded_corps_fails(self, db):
        corps = _make_corps(db, status=CorpsStatus.DISBANDED)
        with pytest.raises(ModeError, match="disbanded"):
            switch_mode(db, corps.id, CorpsMode.DESIGN_ROOM)

    def test_switch_nonexistent_corps_fails(self, db):
        with pytest.raises(ModeError, match="not found"):
            switch_mode(db, "nonexistent", CorpsMode.DESIGN_ROOM)

    def test_switch_creates_work_log(self, db):
        from backend.models.work_log import WorkLog
        corps = _make_corps(db)
        switch_mode(db, corps.id, CorpsMode.DESIGN_ROOM)
        logs = db.query(WorkLog).filter(WorkLog.corps_id == corps.id).all()
        assert len(logs) == 1
        assert logs[0].event_type == "mode_switch"
        assert "design_room" in logs[0].details
