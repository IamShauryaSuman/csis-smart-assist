from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str
    supabase_secret_key: str | None = None
    supabase_service_role_key: str | None = None
    supabase_key: str | None = None
    vector_dimensions: int = 1536
    frontend_origin: str = "http://localhost:3000"
    gemini_api_key: str | None = None
    google_calendar_id: str | None = None
    google_calendar_token_path: str = "calender/token.json"
    admin_seed_emails: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_sender_email: str | None = None
    smtp_sender_password: str | None = None
    rag_local_data_dir: str = "data"
    rag_auto_ingest_local_data: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def supabase_server_key(self) -> str:
        if self.supabase_secret_key:
            return self.supabase_secret_key
        if self.supabase_service_role_key:
            return self.supabase_service_role_key
        if self.supabase_key:
            return self.supabase_key
        raise ValueError(
            "Missing Supabase server key. Set SUPABASE_SECRET_KEY (preferred) or SUPABASE_SERVICE_ROLE_KEY.",
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
