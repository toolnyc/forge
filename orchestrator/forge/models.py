"""Model registry — resolves DB-configured models to pydantic-ai model objects."""

from __future__ import annotations

import os
import time
from typing import Any

from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIModel

from .db import get_db

# Cache: (timestamp, rows)
_cache: tuple[float, list[dict[str, Any]]] | None = None
_CACHE_TTL = 60  # seconds


def get_available_models() -> list[dict[str, Any]]:
    """Read enabled models from model_registry, cached for 60s."""
    global _cache
    now = time.time()
    if _cache and (now - _cache[0]) < _CACHE_TTL:
        return _cache[1]

    db = get_db()
    result = (
        db.table("model_registry")
        .select("*")
        .eq("enabled", True)
        .order("priority")
        .execute()
    )
    rows = result.data or []
    _cache = (now, rows)
    return rows


def resolve_model(name: str) -> Model:
    """Resolve a model name string to a pydantic-ai Model object."""
    models = get_available_models()
    row = next((m for m in models if m["name"] == name), None)

    if row is None:
        # Fallback: try all models (including disabled) from DB
        db = get_db()
        result = db.table("model_registry").select("*").eq("name", name).limit(1).execute()
        row = result.data[0] if result.data else None

    if row is None:
        # Last resort: assume anthropic model
        return AnthropicModel(name)

    return _build_model(row)


def pick_model_for_complexity(complexity: str) -> tuple[str, Model]:
    """Return (model_name, Model) for the highest-priority enabled model matching complexity.

    Complexity hierarchy: complex > standard > trivial.
    A model with max_complexity=complex can handle all levels.
    """
    models = get_available_models()
    complexity_rank = {"trivial": 0, "standard": 1, "complex": 2}
    target = complexity_rank.get(complexity, 1)

    for row in models:  # already sorted by priority
        model_rank = complexity_rank.get(row["max_complexity"], 1)
        if model_rank >= target:
            return row["name"], _build_model(row)

    # Fallback: first enabled model regardless of complexity
    if models:
        return models[0]["name"], _build_model(models[0])

    # No models in DB at all — hardcoded fallback
    return "claude-sonnet-4-6", AnthropicModel("claude-sonnet-4-6")


def _build_model(row: dict[str, Any]) -> Model:
    """Build a pydantic-ai Model from a model_registry row."""
    provider = row["provider"]
    name = row["name"]
    api_key = os.environ.get(row["api_key_env"], "")

    if provider == "anthropic":
        return AnthropicModel(name, api_key=api_key) if api_key else AnthropicModel(name)

    if provider == "openai":
        return OpenAIModel(name, api_key=api_key) if api_key else OpenAIModel(name)

    if provider == "openai_compatible":
        base_url = row.get("base_url")
        return OpenAIModel(name, base_url=base_url, api_key=api_key)

    # Unknown provider — try openai compatible
    return OpenAIModel(name, base_url=row.get("base_url"), api_key=api_key)


def invalidate_cache() -> None:
    """Force re-read from DB on next call."""
    global _cache
    _cache = None
