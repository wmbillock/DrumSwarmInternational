"""Tests for shared YAML utilities."""

import pytest
import yaml

from backend.services.yaml_util import atomic_write, safe_dump_yaml


class TestAtomicWriteRoundtrip:
    def test_write_and_read_matches(self, tmp_path):
        path = tmp_path / "test.yaml"
        data = {"key": "value", "number": 42}
        content = safe_dump_yaml(data)
        atomic_write(path, content)
        loaded = yaml.safe_load(path.read_text())
        assert loaded == data


class TestSafeDumpYamlFormat:
    def test_no_flow_style(self):
        data = {"items": [1, 2, 3]}
        output = safe_dump_yaml(data)
        assert "{" not in output  # no flow style

    def test_keys_not_sorted_alphabetically(self):
        data = {"zebra": 1, "alpha": 2, "middle": 3}
        output = safe_dump_yaml(data)
        lines = [l for l in output.strip().splitlines() if ":" in l]
        keys = [l.split(":")[0] for l in lines]
        assert keys == ["zebra", "alpha", "middle"]


class TestAtomicWriteNoPartialOnError:
    def test_failed_write_preserves_existing(self, tmp_path):
        """If os.replace fails mid-write, the original file is untouched."""
        from unittest.mock import patch

        target = tmp_path / "file.yaml"
        target.write_text("original: true\n")

        # Patch os.replace to simulate a failure after the temp file is written
        with patch("backend.services.yaml_util.os.replace", side_effect=OSError("simulated")):
            with pytest.raises(OSError, match="simulated"):
                atomic_write(target, "corrupted: true\n")

        # Original file should be intact
        assert target.read_text() == "original: true\n"
