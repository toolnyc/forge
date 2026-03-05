"""Tests for the Forge CLI using Typer's CliRunner."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from forge.cli import app


runner = CliRunner()


def _make_db_mock(tasks_data=None):
    db = MagicMock()
    builder = MagicMock()
    builder.select.return_value = builder
    builder.update.return_value = builder
    builder.insert.return_value = builder
    builder.eq.return_value = builder
    builder.order.return_value = builder
    builder.limit.return_value = builder
    builder.single.return_value = builder
    builder.like.return_value = builder
    builder.execute.return_value = MagicMock(data=tasks_data or [])
    db.table.return_value = builder
    return db


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "forge" in result.output.lower() or "Usage" in result.output


def test_tasks_outputs_table():
    tasks_data = [
        {
            "id": "abc12345-0000-0000-0000-000000000000",
            "title": "Research: test topic",
            "status": "complete",
            "model_used": "claude-sonnet-4-6",
            "cost_usd": 0.0012,
            "created_at": "2026-03-05T10:00:00",
        }
    ]
    db_mock = _make_db_mock(tasks_data)

    with patch("forge.cli.get_db", return_value=db_mock):
        result = runner.invoke(app, ["tasks"])

    assert result.exit_code == 0
    assert "Research: test topic" in result.output
    assert "complete" in result.output


def test_tasks_empty_db():
    db_mock = _make_db_mock([])

    with patch("forge.cli.get_db", return_value=db_mock):
        result = runner.invoke(app, ["tasks"])

    assert result.exit_code == 0
    assert "Forge Tasks" in result.output


def test_tasks_status_filter():
    db_mock = _make_db_mock([])

    with patch("forge.cli.get_db", return_value=db_mock):
        result = runner.invoke(app, ["tasks", "--status", "pending"])

    assert result.exit_code == 0
    db_mock.table.return_value.eq.assert_called_with("status", "pending")
