from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://webhook:webhook@localhost:5432/webhook_relay"
    redis_url: str = "redis://localhost:6379/0"
    
    # Sync URL for Alembic (asyncpg -> psycopg2 equivalent)
    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "")

    model_config = {"env_file": ".env"}


settings = Settings()
