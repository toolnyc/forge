"""Forge configuration — loads from environment variables."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    supabase_url: str = field(default_factory=lambda: os.environ["SUPABASE_URL"])
    supabase_key: str = field(default_factory=lambda: os.environ["SUPABASE_SERVICE_KEY"])
    litellm_base_url: str = field(
        default_factory=lambda: os.getenv("LITELLM_BASE_URL", "http://localhost:4000")
    )
    litellm_api_key: str = field(
        default_factory=lambda: os.getenv("LITELLM_API_KEY", "sk-forge-local")
    )
    default_model: str = field(
        default_factory=lambda: os.getenv("DEFAULT_MODEL", "claude-sonnet-4-6")
    )

    @property
    def litellm_model(self) -> str:
        """Model string for litellm routing."""
        return f"litellm_proxy/{self.default_model}"


config = Config()
