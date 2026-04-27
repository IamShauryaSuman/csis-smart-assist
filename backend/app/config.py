from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str
    supabase_secret_key: str | None = None
    supabase_service_role_key: str | None = None
    supabase_key: str | None = None
    vector_dimensions: int = 768
    frontend_origin: str = "http://localhost:3000"
    frontend_origins: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma2:2b"
    embedding_model: str = "nomic-embed-text"
    use_gemini: bool = True
    gemini_api_key: str | None = None
    google_calendar_id: str | None = None
    google_calendar_token_path: str | None = None
    google_calendar_token: str | None = None
    google_calendar_refresh_token: str | None = None
    google_calendar_token_uri: str = "https://oauth2.googleapis.com/token"
    google_calendar_client_id: str | None = None
    google_calendar_client_secret: str | None = None
    google_calendar_service_account_path: str | None = None
    google_calendar_service_account_json: str | None = None
    google_calendar_subject: str | None = None
    
    # Generic Google OAuth (often used for Drive)
    google_token: str | None = None
    google_refresh_token: str | None = None
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_token_uri: str = "https://oauth2.googleapis.com/token"
    google_token_path: str | None = None
    
    google_drive_folder_id: str | None = None
    admin_seed_emails: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    google_sender_email: str | None = None
    smtp_sender_email: str | None = None
    smtp_sender_password: str | None = None
    admin_receiver_email: str | None = None
    google_calendar_id: str | None = None
    google_sender_email: str | None = None
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

    @property
    def cors_origins(self) -> list[str]:
        configured_origins = self.frontend_origins or self.frontend_origin
        parsed_origins = []

        for origin in configured_origins.split(","):
            normalized_origin = origin.strip().strip('"').strip("'").rstrip("/")
            if not normalized_origin:
                continue
            if normalized_origin not in parsed_origins:
                parsed_origins.append(normalized_origin)

        if parsed_origins:
            return parsed_origins

        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
