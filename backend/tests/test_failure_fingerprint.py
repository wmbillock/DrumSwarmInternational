"""Tests for failure fingerprinting."""

from backend.services.failure_fingerprint import FailureFingerprint, FailureRegistry


class TestFailureFingerprint:
    def test_hash_stability(self):
        fp1 = FailureFingerprint(tool_name="create_coordinate", args={"type": "movement"}, error="not found")
        fp2 = FailureFingerprint(tool_name="create_coordinate", args={"type": "movement"}, error="not found")
        assert fp1.key == fp2.key

    def test_different_args_different_hash(self):
        fp1 = FailureFingerprint(tool_name="create_coordinate", args={"type": "movement"}, error="not found")
        fp2 = FailureFingerprint(tool_name="create_coordinate", args={"type": "set"}, error="not found")
        assert fp1.key != fp2.key

    def test_different_errors_different_hash(self):
        fp1 = FailureFingerprint(tool_name="t", args={}, error="error A")
        fp2 = FailureFingerprint(tool_name="t", args={}, error="error B")
        assert fp1.key != fp2.key


class TestFailureRegistry:
    def test_record_and_count(self):
        reg = FailureRegistry(max_retries=2)
        fp = FailureFingerprint(tool_name="t", args={}, error="err")
        assert reg.record_failure(fp) == 1
        assert reg.record_failure(fp) == 2
        assert reg.record_failure(fp) == 3

    def test_should_block_after_threshold(self):
        reg = FailureRegistry(max_retries=2)
        fp = FailureFingerprint(tool_name="t", args={}, error="err")
        assert not reg.should_block(fp)
        reg.record_failure(fp)
        assert not reg.should_block(fp)
        reg.record_failure(fp)
        assert reg.should_block(fp)

    def test_guidance_message(self):
        reg = FailureRegistry(max_retries=1)
        fp = FailureFingerprint(tool_name="create_rep", args={"id": "x"}, error="bad")
        assert reg.get_guidance(fp) is None
        reg.record_failure(fp)
        guidance = reg.get_guidance(fp)
        assert guidance is not None
        assert "FAILURE PATTERN DETECTED" in guidance
        assert "create_rep" in guidance

    def test_persistence_roundtrip(self):
        reg1 = FailureRegistry(max_retries=2)
        fp = FailureFingerprint(tool_name="t", args={"a": 1}, error="err")
        reg1.record_failure(fp)
        reg1.record_failure(fp)
        data = reg1.get_all_fingerprints()

        reg2 = FailureRegistry(max_retries=2)
        reg2.load_fingerprints(data)
        assert reg2.should_block(fp)

    def test_different_fingerprints_independent(self):
        reg = FailureRegistry(max_retries=2)
        fp1 = FailureFingerprint(tool_name="a", args={}, error="x")
        fp2 = FailureFingerprint(tool_name="b", args={}, error="y")
        reg.record_failure(fp1)
        reg.record_failure(fp1)
        assert reg.should_block(fp1)
        assert not reg.should_block(fp2)
