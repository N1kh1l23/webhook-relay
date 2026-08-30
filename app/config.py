from urllib.parse import urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://webhook:webhook@localhost:5432/webhook_relay"
    redis_url: str = "redis://localhost:6379/0"

    # Retry policy. Env-overridable so demo.sh can shorten the curve.
    max_delivery_attempts: int = 6
    retry_base_ms: int = 15_000
    retry_cap_ms: int = 300_000

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        parts = urlsplit(v)
        scheme = parts.scheme
        if parts.scheme == "postgres":
            scheme = "postgresql"
        if "+asyncpg" not in scheme:
            scheme += "+asyncpg"
        return urlunsplit((scheme, parts.netloc, parts.path, "", parts.fragment))

    # Sync URL for Alembic (asyncpg -> psycopg2 equivalent)
    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "")

    model_config = {"env_file": ".env"}


settings = Settings()
