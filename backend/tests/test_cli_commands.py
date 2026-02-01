"""Tests for CLI command parsing and dispatch."""

import pytest
from backend.cli.main import build_parser


class TestParser:
    def test_no_args_returns_none_command(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.command is None

    def test_season_create(self):
        parser = build_parser()
        args = parser.parse_args(["season", "create", "Test Season", "--year", "2026"])
        assert args.command == "season"
        assert args.season_cmd == "create"
        assert args.name == "Test Season"
        assert args.year == 2026

    def test_corps_list(self):
        parser = build_parser()
        args = parser.parse_args(["corps", "list"])
        assert args.command == "corps"
        assert args.corps_cmd == "list"

    def test_corps_status(self):
        parser = build_parser()
        args = parser.parse_args(["corps", "status", "abc123"])
        assert args.corps_cmd == "status"
        assert args.id == "abc123"

    def test_show_create(self):
        parser = build_parser()
        args = parser.parse_args(["show", "create", "My Show", "--description", "A test"])
        assert args.show_cmd == "create"
        assert args.title == "My Show"
        assert args.description == "A test"

    def test_show_activate(self):
        parser = build_parser()
        args = parser.parse_args(["show", "activate", "show-id-1"])
        assert args.show_cmd == "activate"
        assert args.id == "show-id-1"

    def test_show_list(self):
        parser = build_parser()
        args = parser.parse_args(["show", "list"])
        assert args.show_cmd == "list"

    def test_mode_switch(self):
        parser = build_parser()
        args = parser.parse_args(["mode", "switch", "corps-1", "design_room"])
        assert args.mode_cmd == "switch"
        assert args.corps_id == "corps-1"
        assert args.mode == "design_room"

    def test_mode_shortcut_design_room(self):
        parser = build_parser()
        args = parser.parse_args(["mode", "design-room", "corps-1"])
        assert args.mode_cmd == "design-room"
        assert args.corps_id == "corps-1"

    def test_status(self):
        parser = build_parser()
        args = parser.parse_args(["status", "--corps", "abc", "--json"])
        assert args.command == "status"
        assert args.corps == "abc"
        assert args.json is True

    def test_logs(self):
        parser = build_parser()
        args = parser.parse_args(["logs", "corps-1", "--tail", "50"])
        assert args.command == "logs"
        assert args.corps_id == "corps-1"
        assert args.tail == 50

    def test_source(self):
        parser = build_parser()
        args = parser.parse_args(["source", "Build", "a", "REST", "API"])
        assert args.command == "source"
        assert args.task_description == ["Build", "a", "REST", "API"]

    def test_draft_run(self):
        parser = build_parser()
        args = parser.parse_args(["draft", "run", "corps-1"])
        assert args.draft_cmd == "run"
        assert args.corps_id == "corps-1"

    def test_score_submit(self):
        parser = build_parser()
        args = parser.parse_args(["score", "submit", "corps-1", "--caption", "brass", "--value", "85.5"])
        assert args.score_cmd == "submit"
        assert args.corps_id == "corps-1"
        assert args.caption == "brass"
        assert args.value == 85.5
