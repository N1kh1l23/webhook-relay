from pydantic_settings import BaseSettings
from pydantic import field_validator
from urllib.parse import urlsplit, urlunsplit

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://webhook:webhook@localhost:5432/webhook_relay"
    redis_url: str = "redis://localhost:6379/0"

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
