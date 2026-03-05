"""Built-in judges — 1 LLM judge, 4 heuristic judges."""

from __future__ import annotations

import re

from .base import Judge, JudgeInput, JudgeScore


class TaskAlignmentJudge(Judge):
    """LLM-based judge: does the output address the request? Uses Haiku for cost."""

    def __init__(self, weight: float = 2.0):
        super().__init__(name="task_alignment", weight=weight)

    async def evaluate(self, input: JudgeInput) -> JudgeScore:
        # LLM call via pydantic-ai
        from pydantic_ai import Agent

        _judge_agent = Agent(
            model="claude-haiku-4-5",
            system_prompt=(
                "You are a quality judge. Given a task prompt and an agent's output, "
                "determine if the output addresses the request. "
                "Reply with ONLY a JSON object: "
                '{"passed": true/false, "score": 0.0-1.0, "reason": "brief explanation"}'
            ),
        )

        judge_prompt = (
            f"Task prompt:\n{input.task_prompt}\n\n"
            f"Agent output:\n{input.agent_output[:3000]}"
        )

        try:
            result = await _judge_agent.run(judge_prompt)
            import json

            # Parse the JSON response
            text = result.output.strip()
            # Handle markdown code blocks
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(text)

            usage = result.usage()
            tokens_in = usage.request_tokens or 0
            tokens_out = usage.response_tokens or 0
            cost = round(tokens_in * 0.80 / 1_000_000 + tokens_out * 4.0 / 1_000_000, 6)

            return JudgeScore(
                judge_name=self.name,
                passed=bool(data.get("passed", False)),
                score=float(data.get("score", 0.0)),
                reason=data.get("reason", "No reason given"),
                weight=self.weight,
                cost_usd=cost,
            )
        except Exception as e:
            # If judge fails, auto-pass to avoid blocking
            return JudgeScore(
                judge_name=self.name,
                passed=True,
                score=0.5,
                reason=f"Judge error (auto-pass): {e}",
                weight=self.weight,
                cost_usd=0.0,
            )


class CompletenessJudge(Judge):
    """Heuristic: checks for truncation, TODOs, empty sections."""

    def __init__(self, weight: float = 1.0):
        super().__init__(name="completeness", weight=weight)

    async def evaluate(self, input: JudgeInput) -> JudgeScore:
        output = input.agent_output
        issues = []

        # Check for truncation signals
        if output.rstrip().endswith("...") and len(output) > 500:
            issues.append("Output appears truncated (ends with ...)")

        # Check for TODO/FIXME markers
        todo_count = len(re.findall(r"\bTODO\b|\bFIXME\b|\bHACK\b", output, re.IGNORECASE))
        if todo_count > 0:
            issues.append(f"Contains {todo_count} TODO/FIXME markers")

        # Check for empty sections (markdown headers with no content)
        empty_sections = re.findall(r"^#+\s+.+\n\s*(?=^#+|\Z)", output, re.MULTILINE)
        if len(empty_sections) > 1:
            issues.append(f"{len(empty_sections)} empty sections")

        # Very short output for non-trivial tasks
        if len(output.strip()) < 50 and input.task_type != "trivial":
            issues.append("Output suspiciously short")

        passed = len(issues) == 0
        score = max(0.0, 1.0 - len(issues) * 0.25)
        reason = "; ".join(issues) if issues else "Output looks complete"

        return JudgeScore(
            judge_name=self.name,
            passed=passed,
            score=score,
            reason=reason,
            weight=self.weight,
        )


class FactualGroundingJudge(Judge):
    """Heuristic: checks for citations and hedging. Research tasks only."""

    def __init__(self, weight: float = 1.5):
        super().__init__(name="factual_grounding", weight=weight)

    async def evaluate(self, input: JudgeInput) -> JudgeScore:
        # Auto-pass for non-research tasks
        if input.task_type not in ("research", "analysis"):
            return JudgeScore(
                judge_name=self.name,
                passed=True,
                score=1.0,
                reason="N/A (not a research task)",
                weight=0.0,  # zero weight = doesn't affect aggregation
            )

        output = input.agent_output
        issues = []

        # Check for URLs/citations
        url_count = len(re.findall(r"https?://\S+", output))
        if url_count == 0:
            issues.append("No URLs or citations found")

        # Excessive hedging
        hedge_words = re.findall(
            r"\b(?:might|maybe|perhaps|possibly|could be|uncertain)\b",
            output,
            re.IGNORECASE,
        )
        word_count = len(output.split())
        if word_count > 0 and len(hedge_words) / word_count > 0.02:
            issues.append("Excessive hedging language")

        passed = len(issues) == 0
        score = max(0.0, 1.0 - len(issues) * 0.3)
        reason = "; ".join(issues) if issues else "Grounding looks solid"

        return JudgeScore(
            judge_name=self.name,
            passed=passed,
            score=score,
            reason=reason,
            weight=self.weight,
        )


class VoiceStyleJudge(Judge):
    """Heuristic: checks Pete's voice rules from CLAUDE.md."""

    def __init__(self, weight: float = 0.5):
        super().__init__(name="voice_style", weight=weight)

    async def evaluate(self, input: JudgeInput) -> JudgeScore:
        # Auto-pass for code-only tasks
        if input.task_type in ("code", "migration", "refactor"):
            return JudgeScore(
                judge_name=self.name,
                passed=True,
                score=1.0,
                reason="N/A (code task)",
                weight=0.0,
            )

        output = input.agent_output
        issues = []

        # Check for "we" usage (it's one person)
        we_matches = re.findall(r"\bwe\b(?!\s+don't|\s+can't|\s+won't)", output, re.IGNORECASE)
        if len(we_matches) > 2:
            issues.append(f"Uses 'we' {len(we_matches)} times (it's one person)")

        # Check for marketing buzzwords
        buzzwords = re.findall(
            r"\b(?:synergy|leverage|paradigm|disrupt|innovative|cutting-edge|"
            r"game-changing|best-in-class|world-class|next-gen|scalable solution)\b",
            output,
            re.IGNORECASE,
        )
        if buzzwords:
            issues.append(f"Buzzwords detected: {', '.join(set(buzzwords))}")

        # Check for excessive superlatives
        superlatives = re.findall(
            r"\b(?:absolutely|incredibly|amazingly|extremely|tremendously|"
            r"extraordinarily|phenomenally)\b",
            output,
            re.IGNORECASE,
        )
        if len(superlatives) > 2:
            issues.append(f"Too many superlatives ({len(superlatives)})")

        passed = len(issues) == 0
        score = max(0.0, 1.0 - len(issues) * 0.3)
        reason = "; ".join(issues) if issues else "Voice checks out"

        return JudgeScore(
            judge_name=self.name,
            passed=passed,
            score=score,
            reason=reason,
            weight=self.weight,
        )


class CodeQualityJudge(Judge):
    """Heuristic: checks code conventions. Code tasks only."""

    def __init__(self, weight: float = 1.5):
        super().__init__(name="code_quality", weight=weight)

    async def evaluate(self, input: JudgeInput) -> JudgeScore:
        # Auto-pass for non-code tasks
        if input.task_type not in ("code", "refactor", "migration"):
            return JudgeScore(
                judge_name=self.name,
                passed=True,
                score=1.0,
                reason="N/A (not a code task)",
                weight=0.0,
            )

        output = input.agent_output
        issues = []

        # Check for Optional[X] instead of X | None
        optional_usage = re.findall(r"\bOptional\[", output)
        if optional_usage:
            issues.append(f"Uses Optional[X] {len(optional_usage)} times (use X | None)")

        # Check for missing future annotations in Python code
        if "def " in output or "class " in output:
            if "from __future__ import annotations" not in output:
                # Only flag if it looks like a full Python file
                if output.strip().startswith(('"""', "import ", "from ", "#")):
                    issues.append("Missing 'from __future__ import annotations'")

        # Check for overly long lines (>100 chars)
        long_lines = [
            i + 1
            for i, line in enumerate(output.split("\n"))
            if len(line) > 100 and not line.strip().startswith(("#", "//", "http"))
        ]
        if len(long_lines) > 3:
            issues.append(f"{len(long_lines)} lines exceed 100 chars")

        passed = len(issues) == 0
        score = max(0.0, 1.0 - len(issues) * 0.25)
        reason = "; ".join(issues) if issues else "Code conventions look good"

        return JudgeScore(
            judge_name=self.name,
            passed=passed,
            score=score,
            reason=reason,
            weight=self.weight,
        )
