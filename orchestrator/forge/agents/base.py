"""Base agent class wrapping Pydantic AI with Supabase persistence and judge loop."""

from __future__ import annotations

import enum
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models import Model

from ..db import get_db
from ..judges import JudgeInput, JudgePanel, JudgeResult, Verdict
from ..models import resolve_model


class JudgePolicy(enum.Enum):
    """When to run judges on agent output."""

    ALWAYS = "always"
    NEVER = "never"
    AUTO = "auto"  # Run if a panel is configured


class ForgeAgent:
    """Wraps a Pydantic AI Agent with task lifecycle management via Supabase."""

    def __init__(
        self,
        name: str,
        agent: Agent,
        agent_db_id: str | None = None,
        judge_panel: JudgePanel | None = None,
        judge_policy: JudgePolicy = JudgePolicy.AUTO,
        max_retries: int = 2,
        task_type: str = "general",
    ):
        self.name = name
        self.agent = agent
        self.agent_db_id = agent_db_id
        self.judge_panel = judge_panel
        self.judge_policy = judge_policy
        self.max_retries = max_retries
        self.task_type = task_type

    def _should_judge(self) -> bool:
        """Whether to run the judge panel."""
        if self.judge_policy == JudgePolicy.ALWAYS:
            return True
        if self.judge_policy == JudgePolicy.NEVER:
            return False
        # AUTO: run if panel exists
        return self.judge_panel is not None

    async def run_task(
        self,
        task_id: str,
        prompt: str,
        *,
        project_id: str | None = None,
        model: str | None = None,
        task_type: str | None = None,
    ) -> dict[str, Any]:
        """Execute a task: update status, run agent, judge output, store result, log cost."""
        db = get_db()
        effective_task_type = task_type or self.task_type

        # Mark task as running
        db.table("tasks").update({
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "model_used": model or self.agent.model.model_name if hasattr(self.agent, 'model') else None,
            "task_type": effective_task_type,
            "agent_name": self.name,
        }).eq("id", task_id).execute()

        # Load project context if available
        context = ""
        if project_id:
            project = db.table("projects").select("context, name").eq("id", project_id).single().execute()
            if project.data:
                context = f"Project: {project.data['name']}\n\n{project.data['context']}\n\n"

            # Load relevant memories
            memories = db.table("memories").select("content, category").eq("project_id", project_id).execute()
            if memories.data:
                context += "Relevant memories:\n"
                for m in memories.data:
                    context += f"- [{m['category']}] {m['content']}\n"
                context += "\n"

        full_prompt = context + prompt

        try:
            output = await self._run_with_judges(
                task_id=task_id,
                prompt=full_prompt,
                project_id=project_id,
                task_type=effective_task_type,
                model=model,
            )

            return output

        except Exception as e:
            db.table("tasks").update({
                "status": "failed",
                "output": {"error": str(e)},
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", task_id).execute()
            raise

    async def _run_with_judges(
        self,
        task_id: str,
        prompt: str,
        project_id: str | None,
        task_type: str,
        model: str | None,
    ) -> dict[str, Any]:
        """Run agent with optional judge retry loop."""
        db = get_db()
        current_prompt = prompt
        max_attempts = self.max_retries + 1 if self._should_judge() else 1

        for attempt in range(1, max_attempts + 1):
            run_model = resolve_model(model) if model else None
            result = await self.agent.run(current_prompt, model=run_model)
            output_text = result.output
            output = {
                "response": output_text,
                "all_messages_json": result.all_messages_json().decode()
                if isinstance(result.all_messages_json(), bytes)
                else result.all_messages_json(),
            }

            # Extract usage
            usage = result.usage()
            tokens_in = usage.request_tokens or 0
            tokens_out = usage.response_tokens or 0

            # Run judges if applicable
            if self._should_judge() and self.judge_panel:
                judge_input = JudgeInput(
                    task_prompt=prompt,
                    agent_output=output_text,
                    agent_name=self.name,
                    project_id=project_id,
                    task_type=task_type,
                )
                judge_result = await self.judge_panel.evaluate(judge_input, attempt=attempt)
                self._persist_judgment(task_id, attempt, judge_result)

                output["judgment"] = {
                    "verdict": judge_result.verdict.value,
                    "reason": judge_result.reason,
                    "attempt": attempt,
                    "judge_cost": judge_result.total_judge_cost,
                }

                if judge_result.verdict == Verdict.FAIL_RETRY and attempt < max_attempts:
                    # Append retry hint and try again
                    retry_msg = judge_result.retry_hint or judge_result.reason
                    current_prompt = (
                        f"{prompt}\n\n"
                        f"[JUDGE FEEDBACK — attempt {attempt}] "
                        f"Your previous output had issues: {retry_msg}\n"
                        f"Please fix these issues in your response."
                    )
                    continue

                # PASS, ESCALATE, or GIVE_UP — break out
                if judge_result.verdict != Verdict.PASS:
                    output["judgment"]["warning"] = (
                        f"Judge verdict: {judge_result.verdict.value} — {judge_result.reason}"
                    )

            # Persist final result
            cost_usd = self._estimate_cost(tokens_in, tokens_out, model or "claude-sonnet-4-6")
            db.table("tasks").update({
                "status": "complete",
                "output": output,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", task_id).execute()

            db.table("cost_log").insert({
                "id": str(uuid.uuid4()),
                "task_id": task_id,
                "project_id": project_id,
                "model": model or "claude-sonnet-4-6",
                "input_tokens": tokens_in,
                "output_tokens": tokens_out,
                "cost_usd": cost_usd,
            }).execute()

            return output

        # Should not reach here, but safety fallback
        return output  # type: ignore[possibly-undefined]

    def _persist_judgment(self, task_id: str, attempt: int, result: JudgeResult) -> None:
        """Store judgment in Supabase judgments table."""
        try:
            db = get_db()
            db.table("judgments").insert({
                "id": str(uuid.uuid4()),
                "task_id": task_id,
                "attempt": attempt,
                "verdict": result.verdict.value,
                "reason": result.reason,
                "scores": json.dumps([
                    {
                        "judge_name": s.judge_name,
                        "passed": s.passed,
                        "score": s.score,
                        "reason": s.reason,
                        "weight": s.weight,
                        "cost_usd": s.cost_usd,
                    }
                    for s in result.scores
                ]),
                "total_judge_cost": result.total_judge_cost,
            }).execute()
        except Exception:
            # Don't let judgment persistence failure kill the task
            pass

    @staticmethod
    def _estimate_cost(tokens_in: int, tokens_out: int, model: str) -> float:
        """Rough cost estimate per model. LiteLLM will give exact numbers later."""
        rates = {
            "claude-sonnet-4-6": (3.0 / 1_000_000, 15.0 / 1_000_000),
            "claude-haiku-4-5": (0.80 / 1_000_000, 4.0 / 1_000_000),
            "claude-opus-4-6": (15.0 / 1_000_000, 75.0 / 1_000_000),
            "gpt-4o": (2.50 / 1_000_000, 10.0 / 1_000_000),
        }
        in_rate, out_rate = rates.get(model, (3.0 / 1_000_000, 15.0 / 1_000_000))
        return round(tokens_in * in_rate + tokens_out * out_rate, 6)
