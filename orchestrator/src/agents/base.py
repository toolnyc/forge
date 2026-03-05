"""Base agent class wrapping Pydantic AI with Supabase persistence."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models import Model

from ..db import get_db


class ForgeAgent:
    """Wraps a Pydantic AI Agent with task lifecycle management via Supabase."""

    def __init__(
        self,
        name: str,
        agent: Agent,
        agent_db_id: str | None = None,
    ):
        self.name = name
        self.agent = agent
        self.agent_db_id = agent_db_id

    async def run_task(
        self,
        task_id: str,
        prompt: str,
        *,
        project_id: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Execute a task: update status, run agent, store result, log cost."""
        db = get_db()

        # Mark task as running
        db.table("tasks").update({
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "model_used": model or self.agent.model.model_name if hasattr(self.agent, 'model') else None,
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
            result = await self.agent.run(full_prompt)
            output = {
                "response": result.output,
                "all_messages_json": result.all_messages_json(),
            }

            # Extract usage from result
            usage = result.usage()
            tokens_in = usage.request_tokens or 0
            tokens_out = usage.response_tokens or 0

            # Update task with result
            db.table("tasks").update({
                "status": "complete",
                "output": output,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", task_id).execute()

            # Log cost
            cost_usd = self._estimate_cost(tokens_in, tokens_out, model or "claude-sonnet-4-6")
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

        except Exception as e:
            db.table("tasks").update({
                "status": "failed",
                "output": {"error": str(e)},
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", task_id).execute()
            raise

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
