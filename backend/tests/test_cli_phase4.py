"""Tests for Phase 4 CLI commands: watch, batch, export, enhanced source."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import yaml

from backend.cli.main import build_parser


# --- Parser tests ---

class TestPhase4Parser:
    def setup_method(self):
        self.parser = build_parser()

    def test_watch_basic(self):
        args = self.parser.parse_args(["watch", "abc123"])
        assert args.command == "watch"
        assert args.corps_id == "abc123"
        assert args.interval == 2

    def test_watch_with_interval(self):
        args = self.parser.parse_args(["watch", "abc123", "--interval", "5"])
        assert args.interval == 5

    def test_watch_no_follow(self):
        args = self.parser.parse_args(["watch", "abc123", "--no-follow"])
        assert args.no_follow is True

    def test_batch_basic(self):
        args = self.parser.parse_args(["batch", "workflow.yaml"])
        assert args.command == "batch"
        assert args.script == "workflow.yaml"

    def test_batch_dry_run(self):
        args = self.parser.parse_args(["batch", "workflow.yaml", "--dry-run"])
        assert args.dry_run is True

    def test_export_basic(self):
        args = self.parser.parse_args(["export", "abc123"])
        assert args.command == "export"
        assert args.corps_id == "abc123"
        assert args.format == "json"

    def test_export_summary_format(self):
        args = self.parser.parse_args(["export", "abc123", "--format", "summary"])
        assert args.format == "summary"

    def test_export_with_output(self):
        args = self.parser.parse_args(["export", "abc123", "-o", "out.json"])
        assert args.output == "out.json"

    def test_source_with_poll(self):
        args = self.parser.parse_args(["source", "Build", "a", "widget", "--poll"])
        assert args.poll is True
        assert args.poll_interval == 5

    def test_source_with_poll_interval(self):
        args = self.parser.parse_args(["source", "task", "--poll", "--poll-interval", "10"])
        assert args.poll_interval == 10


# --- Batch execution tests ---

class TestBatchCommand:
    def test_batch_executes_steps(self):
        workflow = {
            "name": "test workflow",
            "steps": [
                {"action": "show.create", "title": "Test Show", "label": "Create show", "save_as": "show"},
                {"action": "show.activate", "id": "$show.id", "label": "Activate"},
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(workflow, f)
            f.flush()
            script_path = f.name

        try:
            client = MagicMock()
            client.show_create.return_value = {"id": "show-123", "title": "Test Show"}
            client.show_activate.return_value = {"id": "show-123", "status": "active", "corps_id": "corps-456"}

            from backend.cli.commands.batch import cmd_batch
            args = MagicMock()
            args.script = script_path
            args.dry_run = False

            cmd_batch(client, args)

            client.show_create.assert_called_once_with("Test Show", description=None)
            # The $show.id should resolve to "show-123"
            client.show_activate.assert_called_once_with("show-123")
        finally:
            os.unlink(script_path)

    def test_batch_dry_run(self):
        workflow = {
            "name": "test",
            "steps": [{"action": "show.create", "title": "X", "label": "Create"}],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(workflow, f)
            f.flush()
            script_path = f.name

        try:
            client = MagicMock()
            from backend.cli.commands.batch import cmd_batch
            args = MagicMock()
            args.script = script_path
            args.dry_run = True

            cmd_batch(client, args)

            # In dry run, no client methods should be called
            client.show_create.assert_not_called()
        finally:
            os.unlink(script_path)


# --- Export tests ---

class TestExportCommand:
    def test_export_json_to_file(self):
        client = MagicMock()
        client.corps_status.return_value = {"name": "Test Corps", "status": "active", "mode": "design_room"}
        client.scoresheet.return_value = {"composite": {"final_score": 85.5}}
        client.work_log.return_value = [{"event_type": "task_claimed", "role": "arranger"}]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            out_path = f.name

        try:
            from backend.cli.commands.export import cmd_export
            args = MagicMock()
            args.corps_id = "abc12345-full-id"
            args.format = "json"
            args.output = out_path

            cmd_export(client, args)

            with open(out_path) as f:
                data = json.load(f)
            assert data["corps_id"] == "abc12345-full-id"
            assert data["status"]["name"] == "Test Corps"
        finally:
            os.unlink(out_path)

    def test_export_summary(self):
        client = MagicMock()
        client.corps_status.return_value = {"name": "Test", "status": "active", "mode": "show_mode"}
        client.scoresheet.return_value = {"composite": {"final_score": 90.0, "needs_escalation": False, "needs_rework": False}}
        client.work_log.return_value = []

        from backend.cli.commands.export import cmd_export
        args = MagicMock()
        args.corps_id = "abc12345"
        args.format = "summary"
        args.output = None

        # Just ensure it doesn't crash
        cmd_export(client, args)


# --- Watch tests ---

class TestWatchCommand:
    def test_watch_no_follow(self):
        client = MagicMock()
        client.work_log.return_value = [
            {"id": "1", "event_type": "task_claimed", "role": "arranger", "details": "test", "created_at": "2025-01-01T12:00:00"},
        ]

        from backend.cli.commands.watch import cmd_watch
        args = MagicMock()
        args.corps_id = "abc123"
        args.interval = 2
        args.follow = False

        cmd_watch(client, args)
        client.work_log.assert_called_once_with("abc123", limit=10)
