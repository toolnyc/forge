"""Supabase client and database helpers."""

from supabase import create_client, Client

from .config import config

_client: Client | None = None


def get_db() -> Client:
    """Get or create the Supabase client singleton."""
    global _client
    if _client is None:
        _client = create_client(config.supabase_url, config.supabase_key)
    return _client
