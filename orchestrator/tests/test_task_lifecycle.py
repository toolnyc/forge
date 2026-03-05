"""Tests for ForgeAgent.run_task() lifecycle and cost logging."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forge.agents.base import ForgeAgent


def _make_agent_mock(response: str = "result", tokens_in: int = 100, tokens_out: int = 50):
    """Build a minimal Pydantic AI agent mock."""
    usage = MagicMock()
    usage.request_tokens = tokens_in
    usage.response_tokens = tokens_out

    result = MagicMock()
    result.output = response
    result.all_messages_json.return_value = "[]"
    result.usage.return_value = usage

    agent = MagicMock()
    agent.run = AsyncMock(return_value=result)
    return agent


def _make_db_mock():
    """Supabase client mock with chainable builder."""
    db = MagicMock()
    builder = MagicMock()
    builder.select.return_value = builder
    builder.insert.return_value = builder
    builder.update.return_value = builder
    builder.eq.return_value = builder
    builder.single.return_value = builder
    builder.execute.return_value = MagicMock(data=None)
    db.table.return_value = builder
    return db


@pytest.fixture
def db_mock():
    return _make_db_mock()


@pytest.fixture
def forge_agent(db_mock):
    agent_mock = _make_agent_mock()
    fa = ForgeAgent(name="test_agent", agent=agent_mock)
    with patch("forge.agents.base.get_db", return_value=db_mock):
        yield fa, db_mock


@pytest.mark.asyncio
async def test_run_task_marks_running_then_complete(forge_agent):
    fa, db = forge_agent
    task_id = "task-123"

    with patch("forge.agents.base.get_db", return_value=db):
        await fa.run_task(task_id=task_id, prompt="do a thing")

    # Collect all update() calls (chained as .update(...).eq(...).execute())
    update_calls = [call.args[0] for call in db.table.return_value.update.call_args_list]

    statuses = [c.get("status") for c in update_calls if "status" in c]
    assert "running" in statuses
    assert "complete" in statuses


@pytest.mark.asyncio
async def test_run_task_failed_on_agent_error(forge_agent):
    fa, db = forge_agent
    fa.agent.run = AsyncMock(side_effect=RuntimeError("boom"))

    with patch("forge.agents.base.get_db", return_value=db):
        with pytest.raises(RuntimeError, match="boom"):
            await fa.run_task(task_id="task-err", prompt="fail please")

    update_calls = [call.args[0] for call in db.table.return_value.update.call_args_list]
    statuses = [c.get("status") for c in update_calls if "status" in c]
    assert "failed" in statuses

    # Error message stored in output
    outputs = [c.get("output") for c in update_calls if "output" in c]
    assert any("boom" in str(o) for o in outputs)


@pytest.mark.asyncio
async def test_run_task_logs_cost(forge_agent):
    fa, db = forge_agent

    with patch("forge.agents.base.get_db", return_value=db):
        await fa.run_task(task_id="task-cost", prompt="log my cost")

    # cost_log insert should have been called
    insert_calls = [call.args[0] for call in db.table.return_value.insert.call_args_list]
    assert len(insert_calls) >= 1
    cost_entry = insert_calls[0]
    assert "cost_usd" in cost_entry
    assert cost_entry["cost_usd"] >= 0
    assert "input_tokens" in cost_entry
    assert "output_tokens" in cost_entry


@pytest.mark.asyncio
async def test_run_task_returns_output(forge_agent):
    fa, db = forge_agent

    with patch("forge.agents.base.get_db", return_value=db):
        result = await fa.run_task(task_id="task-out", prompt="give output")

    assert result["response"] == "result"
