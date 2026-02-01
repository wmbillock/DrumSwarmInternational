"""Tests for shared YAML utilities."""

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
        path = tmp_path / "existing.yaml"
        path.write_text("original: true\n")

        # Simulate failure by writing to a read-only directory
        # Instead, verify that if atomic_write raises, the original is intact
        import os
        import stat

        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        target = readonly_dir / "file.yaml"
        target.write_text("original: true\n")

        # Make the directory read-only so mkstemp fails
        readonly_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)
        try:
            try:
                atomic_write(target, "corrupted: true\n")
            except OSError:
                pass
            # Original file should be intact
            assert target.read_text() == "original: true\n"
        finally:
            readonly_dir.chmod(stat.S_IRWXU)
