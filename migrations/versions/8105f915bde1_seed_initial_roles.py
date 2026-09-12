"""seed initial roles

Revision ID: 8105f915bde1
Revises: 3d114019c2ae
Create Date: 2026-09-12 19:55:24.653651

"""
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8105f915bde1'
down_revision: Union[str, None] = '3d114019c2ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Initial roles per Blueprint Part 24. Referenced by ad-hoc table (not the ORM model) so this
# migration keeps working even after the Role model itself changes shape later.
ROLES_TABLE = sa.table(
    "roles",
    sa.column("id", sa.Uuid()),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("created_at", sa.DateTime(timezone=True)),
)

INITIAL_ROLES = [
    ("CUSTOMER", "Customer"),
    ("SITE_ENGINEER", "Site Engineer"),
    ("ESTIMATOR", "Estimator"),
    ("PM", "Project Manager"),
    ("MANAGEMENT", "Management"),
    ("OWNER_ADMIN", "Owner / Admin"),
]


def upgrade() -> None:
    # created_at has no DB-side default (see app/core/db.utcnow) -- raw SQL inserts like this
    # one bypass the ORM's Python-side default entirely, so it must be supplied explicitly here.
    now = datetime.now(timezone.utc)
    op.bulk_insert(
        ROLES_TABLE,
        [{"id": uuid.uuid4(), "code": code, "name": name, "created_at": now} for code, name in INITIAL_ROLES],
    )


def downgrade() -> None:
    codes = [code for code, _ in INITIAL_ROLES]
    op.execute(ROLES_TABLE.delete().where(ROLES_TABLE.c.code.in_(codes)))
