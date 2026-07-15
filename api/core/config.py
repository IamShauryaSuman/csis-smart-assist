"""
Core infrastructure configuration loaded from environment variables.

Uses pydantic-settings for typed, validated configuration with sensible defaults.
All secrets are loaded from the environment — never hard-coded.
"""

from __future__ import annotations

import base64
import json
from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Supabase ────────────────────────────────────────────────────────────
    next_public_supabase_url: str
    supabase_service_role_key: str

    # ── Google Gemini ───────────────────────────────────────────────────────
    gemini_api_key: str

    # ── Google Service Account (Base64-encoded JSON) ────────────────────────
    google_service_account_json_b64: str = ""

    # ── Google Drive ────────────────────────────────────────────────────────
    google_drive_folder_id: str = ""

    # ── Gmail API (OAuth) ───────────────────────────────────────────────────
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_refresh_token: str = ""
    gmail_sender_address: str = "CSIS SmartAssist <noreply@yourdomain.com>"

    # ── Application ─────────────────────────────────────────────────────────
    allowed_email_domain: str = "goa.bits-pilani.ac.in"
    frontend_url: str = "http://localhost:3000"

    # ── Gemini Model Names ──────────────────────────────────────────────────
    gemini_model: str = "gemini-flash-latest"
    gemini_fast_model: str = "gemini-flash-lite-latest"
    gemini_embedding_model: str = "gemini-embedding-001"

    # ── Alternate LLM Providers ─────────────────────────────────────────────
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    @property
    def google_service_account_info(self) -> dict[str, Any]:
        """Decode the base64-encoded service account JSON into a dict."""
        if not self.google_service_account_json_b64:
            return {}
        decoded = base64.b64decode(self.google_service_account_json_b64)
        return json.loads(decoded)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton accessor for application settings."""
    return Settings()
