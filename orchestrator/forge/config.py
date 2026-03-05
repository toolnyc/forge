"""Forge configuration — loads from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    supabase_url: str = field(default_factory=lambda: os.environ["SUPABASE_URL"])
    supabase_key: str = field(
        default_factory=lambda: os.getenv("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
    )
    default_model: str = field(
        default_factory=lambda: os.getenv("DEFAULT_MODEL", "claude-sonnet-4-6")
    )
    telegram_bot_token: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", "")
    )
    telegram_chat_id: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", "")
    )
    api_key: str = field(
        default_factory=lambda: os.getenv("FORGE_API_KEY", "")
    )
    port: int = field(
        default_factory=lambda: int(os.getenv("PORT", "8000"))
    )


config = Config()
