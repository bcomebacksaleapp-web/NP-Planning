from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Falls back to SQLite only if no .env/DATABASE_URL is set. Local dev now has a real
    # Postgres instance (see README) -- .env points at it, so this default rarely applies,
    # but tests/test_migrations.py still uses a throwaway SQLite file deliberately for speed.
    database_url: str = "sqlite:///./local_dev.db"


settings = Settings()
