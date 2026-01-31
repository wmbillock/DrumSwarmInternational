"""Tests for note_router."""

from backend.services.note_router import route_note


def test_music_keywords():
    assert "music" in route_note("Set the tempo to 140 bpm")


def test_visual_keywords():
    assert "visual" in route_note("Move to the next drill formation")


def test_guard_keywords():
    assert "guard" in route_note("Add a rifle toss here")


def test_ge_keywords():
    assert "ge" in route_note("Boost the audience impact")


def test_admin_keywords():
    assert "admin" in route_note("Update the budget for travel")


def test_question_mark():
    tags = route_note("Should we change the budget?")
    assert "questions" in tags
    assert "admin" in tags


def test_multi_tag():
    tags = route_note("brass drill formation?")
    assert tags == ["music", "questions", "visual"]


def test_no_keywords_defaults_admin():
    assert route_note("hello world") == ["admin"]


def test_case_insensitive():
    assert "music" in route_note("BRASS section needs work")
    assert "visual" in route_note("DRILL is looking great")
