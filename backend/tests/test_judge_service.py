"""Tests for judge_service — mock LLM, verify context building, score parsing, fallback."""

import json
import pytest
from unittest.mock import MagicMock, patch

from backend.models.score import JudgeType
from backend.services.judge_service import (
    JudgeContext,
    JudgeResult,
    _parse_judge_response,
    _stub_judge_result,
    invoke_judge,
    judge_corps_performance,
    JUDGE_PROMPTS,
)


class TestParseJudgeResponse:
    def test_valid_json(self):
        response = json.dumps({
            "rep_score": 85,
            "perf_score": 78,
            "feedback": "Strong execution with minor issues.",
            "strengths": ["Good architecture", "Clean code"],
            "weaknesses": ["Lacking tests"],
            "action_items": ["Add unit tests"],
        })
        result = _parse_judge_response(response, JudgeType.BRASS)
        assert result.rep_score == 85
        assert result.perf_score == 78
        assert result.feedback == "Strong execution with minor issues."
        assert len(result.strengths) == 2
        assert result.total_score == (85 + 78) / 2

    def test_json_in_code_block(self):
        response = '```json\n{"rep_score": 90, "perf_score": 80, "feedback": "Great"}\n```'
        result = _parse_judge_response(response, JudgeType.VISUAL)
        assert result.rep_score == 90
        assert result.perf_score == 80

    def test_invalid_json_fallback(self):
        result = _parse_judge_response("not valid json at all", JudgeType.GUARD)
        assert result.rep_score == 45.0
        assert result.perf_score == 35.0
        assert "could not be parsed" in result.feedback

    def test_score_clamping(self):
        response = json.dumps({"rep_score": 150, "perf_score": -10})
        result = _parse_judge_response(response, JudgeType.PERCUSSION)
        assert result.rep_score == 100
        assert result.perf_score == 0


class TestStubJudgeResult:
    def test_deterministic(self):
        r1 = _stub_judge_result(JudgeType.BRASS, "corps1", "show1")
        r2 = _stub_judge_result(JudgeType.BRASS, "corps1", "show1")
        assert r1.rep_score == r2.rep_score
        assert r1.perf_score == r2.perf_score

    def test_different_inputs_different_scores(self):
        r1 = _stub_judge_result(JudgeType.BRASS, "corps1", "show1")
        r2 = _stub_judge_result(JudgeType.BRASS, "corps2", "show1")
        # Scores should differ (extremely unlikely to collide)
        assert r1.rep_score != r2.rep_score or r1.perf_score != r2.perf_score

    def test_score_range(self):
        for jt in JudgeType:
            if jt == JudgeType.TIMING:
                continue
            r = _stub_judge_result(jt, "test-corps", "test-show")
            # Rep: 50-75 base scaled by completeness (default 1.0)
            assert 20 <= r.rep_score <= 75
            # Perf: 30-60 base, scaled more aggressively by completeness
            assert 15 <= r.perf_score <= 60


class TestInvokeJudge:
    def test_successful_llm_call(self):
        mock_client = MagicMock()
        mock_client.chat.return_value = MagicMock(
            content=json.dumps({
                "rep_score": 82, "perf_score": 75,
                "feedback": "Good work",
                "strengths": ["Architecture"],
                "weaknesses": ["Testing"],
                "action_items": ["Add tests"],
            })
        )
        context = JudgeContext(corps_id="c1", show_slug="s1")
        result = invoke_judge(JudgeType.BRASS, context, mock_client)
        assert result.rep_score == 82
        assert result.perf_score == 75
        mock_client.chat.assert_called_once()

    def test_llm_failure_fallback(self):
        mock_client = MagicMock()
        mock_client.chat.side_effect = Exception("LLM unavailable")
        context = JudgeContext(corps_id="c1", show_slug="s1")
        result = invoke_judge(JudgeType.BRASS, context, mock_client)
        # Should get stub scores, not crash
        assert 15 <= result.rep_score <= 75
        assert "Stub score" in result.feedback


class TestJudgeCorpsPerformance:
    @patch("backend.services.judge_service.build_judge_context")
    @patch("backend.services.judge_service.ENABLE_REAL_JUDGING", False)
    def test_stub_mode(self, mock_build):
        mock_build.return_value = JudgeContext(corps_id="c1", show_slug="s1")
        db = MagicMock()
        results = judge_corps_performance(db, "c1", "s1", llm_client=MagicMock())
        # Should have all caption types except TIMING
        assert JudgeType.BRASS in results
        assert JudgeType.PERCUSSION in results
        assert JudgeType.ENSEMBLE_TECHNIQUE in results
        assert JudgeType.TIMING not in results

    @patch("backend.services.judge_service.build_judge_context")
    def test_no_llm_client_uses_stubs(self, mock_build):
        mock_build.return_value = JudgeContext(corps_id="c1", show_slug="s1")
        db = MagicMock()
        results = judge_corps_performance(db, "c1", "s1", llm_client=None)
        assert all("Stub score" in r.feedback for r in results.values())


class TestJudgePrompts:
    def test_all_captions_have_prompts(self):
        for jt in JudgeType:
            if jt == JudgeType.TIMING:
                continue
            assert jt in JUDGE_PROMPTS, f"Missing prompt for {jt.value}"

    def test_ensemble_technique_exists(self):
        assert JudgeType.ENSEMBLE_TECHNIQUE in JUDGE_PROMPTS
        assert "delegate" in JUDGE_PROMPTS[JudgeType.ENSEMBLE_TECHNIQUE].lower()
