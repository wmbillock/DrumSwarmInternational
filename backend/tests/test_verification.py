"""Tests for verification gates."""

from backend.services.verification import (
    VerificationEngine, gate_non_empty, gate_minimum_length,
    gate_json_valid, gate_brown_m_and_m,
)


class TestGates:
    def test_non_empty_passes(self):
        r = gate_non_empty("some result")
        assert r.passed

    def test_non_empty_fails(self):
        r = gate_non_empty("")
        assert not r.passed
        r = gate_non_empty("   ")
        assert not r.passed

    def test_minimum_length_passes(self):
        r = gate_minimum_length("a" * 10, min_length=10)
        assert r.passed

    def test_minimum_length_fails(self):
        r = gate_minimum_length("short", min_length=10)
        assert not r.passed

    def test_json_valid_passes_json(self):
        r = gate_json_valid('{"key": "value"}')
        assert r.passed

    def test_json_valid_fails_bad_json(self):
        r = gate_json_valid('{bad json}')
        assert not r.passed

    def test_json_valid_skips_non_json(self):
        r = gate_json_valid("just a regular string")
        assert r.passed
        assert "skipped" in r.message.lower()

    def test_brown_m_and_m_passes(self):
        r = gate_brown_m_and_m("The answer is CANARY42 and more", canary_phrase="CANARY42")
        assert r.passed

    def test_brown_m_and_m_fails(self):
        r = gate_brown_m_and_m("no canary here", canary_phrase="CANARY42")
        assert not r.passed

    def test_brown_m_and_m_no_phrase(self):
        r = gate_brown_m_and_m("anything")
        assert r.passed


class TestVerificationEngine:
    def test_all_gates_pass(self):
        engine = VerificationEngine()
        result = engine.verify("rep-1", "a" * 20)
        assert result.passed
        assert len(result.failed_gates) == 0

    def test_empty_result_fails(self):
        engine = VerificationEngine()
        result = engine.verify("rep-1", "")
        assert not result.passed
        assert any(g.gate_name == "non_empty" for g in result.failed_gates)

    def test_canary_phrase(self):
        engine = VerificationEngine()
        result = engine.verify("rep-1", "a" * 20, canary_phrase="magic")
        assert not result.passed
        assert any(g.gate_name == "brown_m_and_m" for g in result.failed_gates)

        result = engine.verify("rep-1", "a" * 20 + " magic", canary_phrase="magic")
        assert result.passed

    def test_custom_gate(self):
        engine = VerificationEngine()
        from backend.services.verification import GateResult
        def custom(result, **kw):
            return GateResult(gate_name="custom", passed="ANSWER" in result)
        engine.add_custom_gate("coord-1", custom)
        result = engine.verify("rep-1", "a" * 20, segment_id="coord-1")
        assert not result.passed

        result = engine.verify("rep-1", "ANSWER" + "a" * 20, segment_id="coord-1")
        assert result.passed

    def test_summary(self):
        engine = VerificationEngine()
        result = engine.verify("rep-1", "")
        assert "failed" in result.summary.lower()
