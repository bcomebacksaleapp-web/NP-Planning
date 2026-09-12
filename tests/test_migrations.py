import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _run_alembic(*args: str, database_url: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=PROJECT_ROOT,
        env={**__import__("os").environ, "DATABASE_URL": database_url},
        capture_output=True,
        text=True,
    )


def test_migrations_upgrade_then_downgrade_round_trip(tmp_path):
    """Every migration must be reversible (Law 15 / Blueprint Phase 0 acceptance criteria).

    Runs against a throwaway SQLite file, not the dev DB, so this is safe to run repeatedly
    and in CI without a real Postgres instance available.
    """
    db_path = tmp_path / "migration_test.db"
    database_url = f"sqlite:///{db_path}"

    upgraded = _run_alembic("upgrade", "head", database_url=database_url)
    assert upgraded.returncode == 0, upgraded.stderr

    downgraded = _run_alembic("downgrade", "base", database_url=database_url)
    assert downgraded.returncode == 0, downgraded.stderr
