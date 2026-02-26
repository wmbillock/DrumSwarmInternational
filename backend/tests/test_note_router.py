"""Tests for note_router."""

from backend.services.note_router import route_note


def test_architecture_keywords():
    assert "architecture" in route_note("Set the tempo to 140 bpm")
    assert "architecture" in route_note("We need a new API endpoint for this")
    assert "architecture" in route_note("The data model needs a migration")


def test_interface_keywords():
    assert "interface" in route_note("Move to the next drill formation")
    assert "interface" in route_note("Add a new React component for the sidebar")
    assert "interface" in route_note("The frontend layout needs work")


def test_quality_keywords():
    assert "quality" in route_note("Add a rifle toss here")
    assert "quality" in route_note("We need more test coverage")
    assert "quality" in route_note("What about edge cases for empty input?")


def test_ge_keywords():
    assert "ge" in route_note("Boost the audience impact")
    assert "ge" in route_note("User experience needs improvement")


def test_admin_keywords():
    assert "admin" in route_note("Update the budget for travel")
    assert "admin" in route_note("What's the deadline for this milestone?")


def test_question_mark():
    tags = route_note("Should we change the budget?")
    assert "questions" in tags
    assert "admin" in tags


def test_multi_tag():
    tags = route_note("The API endpoint needs a new React component")
    assert "architecture" in tags
    assert "interface" in tags


def test_no_keywords_defaults_admin():
    assert route_note("hello world") == ["admin"]


def test_case_insensitive():
    assert "architecture" in route_note("BACKEND service needs work")
    assert "interface" in route_note("FRONTEND is looking great")
    assert "quality" in route_note("Need more TESTING")
