"""Core judge types — Verdict, JudgeInput, JudgeScore, JudgeResult, Judge ABC."""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class Verdict(enum.Enum):
    """Outcome of a judge panel evaluation."""

    PASS = "pass"
    FAIL_RETRY = "fail_retry"
    ESCALATE = "escalate"
    GIVE_UP = "give_up"


@dataclass
class JudgeInput:
    """What gets fed to each judge."""

    task_prompt: str
    agent_output: str
    agent_name: str
    project_id: str | None = None
    task_type: str = "general"
    metadata: dict = field(default_factory=dict)


@dataclass
class JudgeScore:
    """A single judge's evaluation."""

    judge_name: str
    passed: bool
    score: float  # 0-1
    reason: str
    weight: float = 1.0
    cost_usd: float = 0.0


@dataclass
class JudgeResult:
    """Aggregated result from a judge panel."""

    verdict: Verdict
    scores: list[JudgeScore]
    reason: str
    retry_hint: str | None = None
    total_judge_cost: float = 0.0


class Judge(ABC):
    """Abstract base for all judges."""

    name: str
    weight: float

    def __init__(self, name: str, weight: float = 1.0):
        self.name = name
        self.weight = weight

    @abstractmethod
    async def evaluate(self, input: JudgeInput) -> JudgeScore:
        """Evaluate agent output. Return JudgeScore."""
        ...
