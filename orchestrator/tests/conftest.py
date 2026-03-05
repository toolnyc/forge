"""Shared pytest fixtures for Forge orchestrator tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_db():
    """Return a mock Supabase client with chainable query builder."""
    db = MagicMock()

    # Make table() return a builder that supports chaining
    builder = MagicMock()
    builder.select.return_value = builder
    builder.insert.return_value = builder
    builder.update.return_value = builder
    builder.eq.return_value = builder
    builder.like.return_value = builder
    builder.order.return_value = builder
    builder.limit.return_value = builder
    builder.single.return_value = builder
    builder.execute.return_value = MagicMock(data=[])

    db.table.return_value = builder
    return db


@pytest.fixture
def patch_db(mock_db):
    """Patch get_db() to return mock_db for the duration of the test."""
    with patch("forge.db.get_db", return_value=mock_db):
        yield mock_db
