"""Aggregation strategies for combining judge scores into a verdict."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .base import JudgeScore, Verdict


class Aggregator(ABC):
    """Combines multiple JudgeScores into a single Verdict."""

    @abstractmethod
    def aggregate(self, scores: list[JudgeScore], attempt: int, max_retries: int) -> tuple[Verdict, str]:
        """Return (verdict, reason) from the collected scores."""
        ...


class AllMustPass(Aggregator):
    """Every judge must pass. Any failure triggers retry."""

    def aggregate(self, scores: list[JudgeScore], attempt: int, max_retries: int) -> tuple[Verdict, str]:
        failed = [s for s in scores if not s.passed]
        if not failed:
            return Verdict.PASS, "All judges passed."

        reasons = "; ".join(f"{s.judge_name}: {s.reason}" for s in failed)
        if attempt >= max_retries:
            return Verdict.GIVE_UP, f"Max retries reached. Failures: {reasons}"
        return Verdict.FAIL_RETRY, f"Failed judges: {reasons}"


class WeightedThreshold(Aggregator):
    """Weighted average of scores must meet threshold."""

    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold

    def aggregate(self, scores: list[JudgeScore], attempt: int, max_retries: int) -> tuple[Verdict, str]:
        total_weight = sum(s.weight for s in scores)
        if total_weight == 0:
            return Verdict.PASS, "No weighted judges."

        weighted_avg = sum(s.score * s.weight for s in scores) / total_weight

        if weighted_avg >= self.threshold:
            return Verdict.PASS, f"Weighted score {weighted_avg:.2f} >= {self.threshold}"

        failed = [s for s in scores if not s.passed]
        reasons = "; ".join(f"{s.judge_name}: {s.reason}" for s in failed)
        if attempt >= max_retries:
            return Verdict.GIVE_UP, f"Weighted score {weighted_avg:.2f} < {self.threshold}. {reasons}"
        return Verdict.FAIL_RETRY, f"Weighted score {weighted_avg:.2f} < {self.threshold}. {reasons}"
