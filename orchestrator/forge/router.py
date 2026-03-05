"""Task router — classifies complexity, picks agent and model."""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass


class TaskComplexity(enum.Enum):
    """How complex a task is, drives model selection."""

    TRIVIAL = "trivial"
    STANDARD = "standard"
    COMPLEX = "complex"


@dataclass
class RouteDecision:
    """Where to route a task."""

    agent_name: str
    model: str
    task_type: str
    complexity: TaskComplexity
    reason: str


# Keywords that signal complexity levels
_COMPLEX_SIGNALS = re.compile(
    r"\b(?:architect|redesign|migrate|refactor|integrate|multi-step|compare\s+\d+|"
    r"analyze.*(?:system|architecture)|build.*(?:from scratch|pipeline|framework))\b",
    re.IGNORECASE,
)
_TRIVIAL_SIGNALS = re.compile(
    r"\b(?:what is|define|list|who is|when did|simple|quick|lookup|check)\b",
    re.IGNORECASE,
)

# Keywords that map to agents
_AGENT_KEYWORDS: dict[str, list[str]] = {
    "research": ["research", "find out", "look up", "investigate", "what is", "who is", "compare"],
    "content": ["write", "draft", "blog", "post", "linkedin", "tweet", "email", "copy"],
    "code": ["implement", "fix", "refactor", "debug", "code", "function", "api", "endpoint"],
}

# Keywords that map to task types
_TASK_TYPE_KEYWORDS: dict[str, list[str]] = {
    "research": ["research", "find", "investigate", "analyze", "compare", "what", "who", "when"],
    "content": ["write", "draft", "blog", "post", "email", "copy", "article", "linkedin"],
    "code": ["implement", "fix", "refactor", "debug", "code", "build", "deploy", "migrate"],
}


def classify_complexity(prompt: str) -> TaskComplexity:
    """Classify task complexity via keyword heuristics. No LLM call."""
    if _COMPLEX_SIGNALS.search(prompt):
        return TaskComplexity.COMPLEX
    if _TRIVIAL_SIGNALS.search(prompt):
        return TaskComplexity.TRIVIAL
    return TaskComplexity.STANDARD


def pick_agent(prompt: str) -> str:
    """Pick an agent based on keyword matching. Falls back to 'research'."""
    prompt_lower = prompt.lower()
    scores: dict[str, int] = {}
    for agent, keywords in _AGENT_KEYWORDS.items():
        scores[agent] = sum(1 for kw in keywords if kw in prompt_lower)

    if not any(scores.values()):
        return "research"
    return max(scores, key=lambda k: scores[k])


def pick_task_type(prompt: str) -> str:
    """Infer task type from prompt keywords."""
    prompt_lower = prompt.lower()
    scores: dict[str, int] = {}
    for task_type, keywords in _TASK_TYPE_KEYWORDS.items():
        scores[task_type] = sum(1 for kw in keywords if kw in prompt_lower)

    if not any(scores.values()):
        return "general"
    return max(scores, key=lambda k: scores[k])


def pick_model(complexity: TaskComplexity, budget_remaining: float | None = None) -> str:
    """Map complexity to model via model registry, with budget pressure override."""
    if budget_remaining is not None and budget_remaining < 0.50:
        complexity = TaskComplexity.TRIVIAL

    try:
        from .models import pick_model_for_complexity
        name, _ = pick_model_for_complexity(complexity.value)
        return name
    except Exception:
        # Fallback if model_registry table doesn't exist yet
        return {
            TaskComplexity.TRIVIAL: "claude-haiku-4-5",
            TaskComplexity.STANDARD: "claude-sonnet-4-6",
            TaskComplexity.COMPLEX: "claude-sonnet-4-6",
        }[complexity]


def route(prompt: str, budget_remaining: float | None = None) -> RouteDecision:
    """Main entry point: classify, pick agent/model, return decision."""
    complexity = classify_complexity(prompt)
    agent_name = pick_agent(prompt)
    task_type = pick_task_type(prompt)
    model = pick_model(complexity, budget_remaining)

    reason = f"Complexity={complexity.value}, agent={agent_name}, type={task_type}"
    if budget_remaining is not None and budget_remaining < 0.50:
        reason += f", budget_pressure (${budget_remaining:.2f} remaining)"

    return RouteDecision(
        agent_name=agent_name,
        model=model,
        task_type=task_type,
        complexity=complexity,
        reason=reason,
    )
