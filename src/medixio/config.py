from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///data/medixio.db"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    tz_display: str = "America/Bogota"
    log_level: str = "INFO"
    json_logs: bool = False
    observability_db: str = "data/observability.db"
    observability_retention_days: int = 30

    anthropic_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "CLAUDE_API_KEY"),
    )
    anthropic_model: str = Field(
        default="claude-sonnet-5-5",
        validation_alias=AliasChoices("ANTHROPIC_MODEL", "MODEL"),
    )
    history_size: int = 20
    admin_token: str | None = None

    # Abuse / cost protection (see medixio.ratelimit)
    rate_msgs_per_10min: int = 15
    rate_msgs_per_day: int = 150
    rate_images_per_day: int = 10
    rate_signups_per_hour: int = 20
    max_message_chars: int = 2000
    daily_token_budget: int = 2_000_000

    whatsapp_enabled: bool = True
    wa_session_db: str = "data/wa_session/session.sqlite3"

    scheduler_enabled: bool = True
    scheduler_tick_seconds: int = 60
    quiet_hours_start: int = 21
    quiet_hours_end: int = 7


@lru_cache
def get_settings() -> Settings:
    return Settings()
