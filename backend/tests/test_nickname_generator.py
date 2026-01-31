"""Tests for nickname and name generation."""

from backend.services.nickname_generator import (
    generate_corps_name,
    generate_mascot,
    generate_nickname,
)


class TestCorpsName:
    def test_generates_string(self):
        name = generate_corps_name()
        assert isinstance(name, str)
        assert name.startswith("The ")

    def test_avoids_existing(self):
        first = generate_corps_name()
        second = generate_corps_name(existing={first})
        assert second != first

    def test_uniqueness(self):
        names = {generate_corps_name() for _ in range(20)}
        assert len(names) >= 15  # high uniqueness rate


class TestMascot:
    def test_generates_string(self):
        name = generate_mascot()
        assert isinstance(name, str)
        assert name.startswith("The ")

    def test_avoids_existing(self):
        first = generate_mascot()
        second = generate_mascot(existing={first})
        assert second != first


class TestNickname:
    def test_staff_nickname(self):
        name = generate_nickname("executive_director")
        assert "Director" in name

    def test_member_nickname(self):
        name = generate_nickname("performer")
        assert isinstance(name, str)
        assert len(name) > 3

    def test_avoids_existing(self):
        first = generate_nickname("brass_tech")
        second = generate_nickname("brass_tech", existing={first})
        assert second != first
