from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Falls back to SQLite only if no .env/DATABASE_URL is set. Local dev now has a real
    # Postgres instance (see README) -- .env points at it, so this default rarely applies,
    # but tests/test_migrations.py still uses a throwaway SQLite file deliberately for speed.
    database_url: str = "sqlite:///./local_dev.db"

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, value: str) -> str:
        # Hosting platforms (Railway, Render, Heroku-style) hand out bare postgres:// or
        # postgresql:// URLs -- SQLAlchemy then defaults to psycopg2, which isn't installed
        # (we use psycopg 3). Rewriting the scheme here means the raw platform-provided URL
        # can be used as-is instead of requiring it to be hand-edited in every environment.
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value[len("postgres://"):]
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value[len("postgresql://"):]
        return value


settings = Settings()
