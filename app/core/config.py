from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # No Postgres instance is available on the current dev machine yet (no Docker, no local
    # install found). Defaulting to a local SQLite file keeps Sprint 0.1 runnable without one.
    # Postgres is still the target production dialect -- set DATABASE_URL to override before
    # Sprint 0.2 adds real tables, since SQLite silently tolerates schema changes Postgres would
    # reject (e.g. loose ALTER TABLE semantics), which would hide migration bugs.
    database_url: str = "sqlite:///./local_dev.db"


settings = Settings()
