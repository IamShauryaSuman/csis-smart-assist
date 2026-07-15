"""
Supabase client initialization.

Uses the service-role key to bypass RLS for backend operations.
Each request gets access to the shared client instance.
"""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from core.config import get_settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Return a cached Supabase admin client (service-role)."""
    settings = get_settings()
    return create_client(
        settings.next_public_supabase_url,
        settings.supabase_service_role_key,
    )
