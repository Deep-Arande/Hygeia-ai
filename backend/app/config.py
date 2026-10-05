"""Application settings, loaded from environment / .env.

Two database URLs exist on purpose (see README):
- `database_url`      -> Supabase DIRECT connection (port 5432). Used by Alembic migrations.
- `database_pool_url` -> Supabase POOLER, transaction mode (port 6543). Used by the app at runtime.

The app prefers the pooler and falls back to the direct URL when the pooler is not set.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    app_name: str = "AI Health Agent"
    environment: str = "development"

    # --- Database ---
    # Direct connection (migrations). Empty default keeps imports working in CI/lint
    # before a real .env exists; it is validated where actually used.
    database_url: str = ""
    # Pooler connection (app runtime). Falls back to database_url when unset.
    database_pool_url: str | None = None

    # --- AI / agent (Phase 1) ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    # Bump when the agent's prompts change — stamped on logs for traceability.
    prompt_version: str = "v1"

    # --- Observability: Langfuse (Phase 1) ---
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    @property
    def runtime_database_url(self) -> str:
        """URL the app uses at runtime — pooler if available, else direct."""
        return self.database_pool_url or self.database_url

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


settings = Settings()
