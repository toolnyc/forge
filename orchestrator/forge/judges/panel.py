"""JudgePanel — runs judges concurrently and aggregates results."""

from __future__ import annotations

import asyncio

from .aggregator import Aggregator, AllMustPass
from .base import Judge, JudgeInput, JudgeResult, Verdict


class JudgePanel:
    """Runs a list of judges concurrently, aggregates into a JudgeResult."""

    def __init__(
        self,
        judges: list[Judge],
        aggregator: Aggregator | None = None,
        max_retries: int = 2,
    ):
        self.judges = judges
        self.aggregator = aggregator or AllMustPass()
        self.max_retries = max_retries

    async def evaluate(self, input: JudgeInput, attempt: int = 1) -> JudgeResult:
        """Run all judges concurrently, aggregate scores, build result."""
        scores = await asyncio.gather(*(j.evaluate(input) for j in self.judges))
        scores = list(scores)

        total_cost = sum(s.cost_usd for s in scores)
        verdict, reason = self.aggregator.aggregate(scores, attempt, self.max_retries)

        retry_hint = None
        if verdict == Verdict.FAIL_RETRY:
            failed = [s for s in scores if not s.passed]
            hints = [s.reason for s in failed if s.reason]
            retry_hint = "Fix these issues: " + "; ".join(hints) if hints else None

        return JudgeResult(
            verdict=verdict,
            scores=scores,
            reason=reason,
            retry_hint=retry_hint,
            total_judge_cost=total_cost,
        )
