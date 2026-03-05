"""Tests for the judge system — each judge, both aggregators, panel."""

from __future__ import annotations

import asyncio

import pytest

from forge.judges import (
    AllMustPass,
    CompletenessJudge,
    CodeQualityJudge,
    FactualGroundingJudge,
    JudgeInput,
    JudgePanel,
    JudgeScore,
    Verdict,
    VoiceStyleJudge,
    WeightedThreshold,
)


# --- Fixtures ---

def _input(
    output: str = "A solid research report with findings.",
    task_type: str = "general",
    prompt: str = "Research Pydantic AI",
) -> JudgeInput:
    return JudgeInput(
        task_prompt=prompt,
        agent_output=output,
        agent_name="test_agent",
        task_type=task_type,
    )


# --- CompletenessJudge ---

class TestCompletenessJudge:
    @pytest.fixture
    def judge(self):
        return CompletenessJudge()

    def test_pass_normal_output(self, judge):
        inp = _input("This is a complete research report with multiple findings and details.")
        score = asyncio.run(judge.evaluate(inp))
        assert score.passed
        assert score.score == 1.0

    def test_fail_truncated(self, judge):
        inp = _input("x" * 600 + "...")
        score = asyncio.run(judge.evaluate(inp))
        assert not score.passed
        assert "truncated" in score.reason.lower()

    def test_fail_todos(self, judge):
        inp = _input("Here is the report.\nTODO: add more details\nFIXME: broken link")
        score = asyncio.run(judge.evaluate(inp))
        assert not score.passed
        assert "TODO" in score.reason

    def test_fail_short_output(self, judge):
        inp = _input("OK.")
        score = asyncio.run(judge.evaluate(inp))
        assert not score.passed
        assert "short" in score.reason.lower()


# --- FactualGroundingJudge ---

class TestFactualGroundingJudge:
    @pytest.fixture
    def judge(self):
        return FactualGroundingJudge()

    def test_auto_pass_non_research(self, judge):
        inp = _input("Some code output", task_type="code")
        score = asyncio.run(judge.evaluate(inp))
        assert score.passed
        assert score.weight == 0.0  # zero weight = doesn't affect aggregation

    def test_pass_with_urls(self, judge):
        inp = _input(
            "According to https://example.com, Pydantic AI is great. "
            "See also https://docs.pydantic.dev for details.",
            task_type="research",
        )
        score = asyncio.run(judge.evaluate(inp))
        assert score.passed

    def test_fail_no_urls(self, judge):
        inp = _input("Pydantic AI is a framework for building agents.", task_type="research")
        score = asyncio.run(judge.evaluate(inp))
        assert not score.passed
        assert "citation" in score.reason.lower() or "URL" in score.reason


# --- VoiceStyleJudge ---

class TestVoiceStyleJudge:
    @pytest.fixture
    def judge(self):
        return VoiceStyleJudge()

    def test_auto_pass_code_task(self, judge):
        inp = _input("def foo(): pass", task_type="code")
        score = asyncio.run(judge.evaluate(inp))
        assert score.passed
        assert score.weight == 0.0

    def test_pass_clean_voice(self, judge):
        inp = _input("Built the dashboard. Ships Monday. No dependencies on external APIs.")
        score = asyncio.run(judge.evaluate(inp))
        assert score.passed

    def test_fail_we_usage(self, judge):
        inp = _input(
            "We believe that we can leverage our synergy to build "
            "we think we should we will we can"
        )
        score = asyncio.run(judge.evaluate(inp))
        assert not score.passed

    def test_fail_buzzwords(self, judge):
        inp = _input("This cutting-edge, game-changing paradigm will disrupt the industry.")
        score = asyncio.run(judge.evaluate(inp))
        assert not score.passed
        assert "buzzword" in score.reason.lower()


# --- CodeQualityJudge ---

class TestCodeQualityJudge:
    @pytest.fixture
    def judge(self):
        return CodeQualityJudge()

    def test_auto_pass_non_code(self, judge):
        inp = _input("A research report.", task_type="research")
        score = asyncio.run(judge.evaluate(inp))
        assert score.passed
        assert score.weight == 0.0

    def test_pass_clean_code(self, judge):
        code = '''"""Module doc."""

from __future__ import annotations

def hello(name: str | None = None) -> str:
    return f"Hello, {name or 'world'}!"
'''
        inp = _input(code, task_type="code")
        score = asyncio.run(judge.evaluate(inp))
        assert score.passed

    def test_fail_optional_usage(self, judge):
        code = '''"""Module."""

from __future__ import annotations
from typing import Optional

def hello(name: Optional[str] = None) -> str:
    return f"Hello, {name or 'world'}!"
'''
        inp = _input(code, task_type="code")
        score = asyncio.run(judge.evaluate(inp))
        assert not score.passed
        assert "Optional" in score.reason


# --- AllMustPass Aggregator ---

class TestAllMustPass:
    def test_all_pass(self):
        scores = [
            JudgeScore("a", True, 1.0, "ok", 1.0),
            JudgeScore("b", True, 0.9, "ok", 1.0),
        ]
        verdict, reason = AllMustPass().aggregate(scores, attempt=1, max_retries=2)
        assert verdict == Verdict.PASS

    def test_one_fails_retries(self):
        scores = [
            JudgeScore("a", True, 1.0, "ok", 1.0),
            JudgeScore("b", False, 0.3, "bad output", 1.0),
        ]
        verdict, reason = AllMustPass().aggregate(scores, attempt=1, max_retries=2)
        assert verdict == Verdict.FAIL_RETRY

    def test_one_fails_max_retries(self):
        scores = [
            JudgeScore("a", True, 1.0, "ok", 1.0),
            JudgeScore("b", False, 0.3, "bad output", 1.0),
        ]
        verdict, reason = AllMustPass().aggregate(scores, attempt=2, max_retries=2)
        assert verdict == Verdict.GIVE_UP


# --- WeightedThreshold Aggregator ---

class TestWeightedThreshold:
    def test_above_threshold(self):
        scores = [
            JudgeScore("a", True, 0.9, "ok", 2.0),
            JudgeScore("b", True, 0.8, "ok", 1.0),
        ]
        verdict, _ = WeightedThreshold(0.7).aggregate(scores, attempt=1, max_retries=2)
        assert verdict == Verdict.PASS

    def test_below_threshold(self):
        scores = [
            JudgeScore("a", False, 0.3, "bad", 2.0),
            JudgeScore("b", True, 0.8, "ok", 1.0),
        ]
        # Weighted avg: (0.3*2 + 0.8*1) / 3 = 0.467
        verdict, _ = WeightedThreshold(0.7).aggregate(scores, attempt=1, max_retries=2)
        assert verdict == Verdict.FAIL_RETRY

    def test_zero_weight(self):
        scores = [
            JudgeScore("a", True, 1.0, "ok", 0.0),
            JudgeScore("b", True, 1.0, "ok", 0.0),
        ]
        verdict, _ = WeightedThreshold(0.7).aggregate(scores, attempt=1, max_retries=2)
        assert verdict == Verdict.PASS  # no weighted judges → auto pass


# --- JudgePanel ---

class TestJudgePanel:
    def test_panel_all_pass(self):
        panel = JudgePanel(
            judges=[CompletenessJudge(), VoiceStyleJudge()],
            aggregator=AllMustPass(),
        )
        inp = _input("A thorough and complete report on the topic with real findings.")
        result = asyncio.run(panel.evaluate(inp))
        assert result.verdict == Verdict.PASS
        assert len(result.scores) == 2
        assert result.total_judge_cost == 0.0  # all heuristic judges

    def test_panel_with_failure(self):
        panel = JudgePanel(
            judges=[CompletenessJudge()],
            aggregator=AllMustPass(),
            max_retries=1,
        )
        inp = _input("OK.")  # too short
        result = asyncio.run(panel.evaluate(inp, attempt=1))
        assert result.verdict == Verdict.GIVE_UP  # max_retries=1, attempt=1
        assert result.scores[0].passed is False

    def test_panel_concurrent_execution(self):
        """Verify all judges run (result has correct count)."""
        panel = JudgePanel(
            judges=[
                CompletenessJudge(),
                VoiceStyleJudge(),
                CodeQualityJudge(),
                FactualGroundingJudge(),
            ],
        )
        inp = _input("A normal output.", task_type="general")
        result = asyncio.run(panel.evaluate(inp))
        assert len(result.scores) == 4
