"""link quote lines to product

Revision ID: 8c13f4750ea9
Revises: b5866c9c253f
Create Date: 2026-09-12 22:41:35.817784

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c13f4750ea9'
down_revision: Union[str, None] = 'b5866c9c253f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # batch_alter_table for the same reason as Sprint 0.8's project-lifecycle-state migration:
    # SQLite has no ALTER-based way to add a foreign key constraint at all (plain
    # create_foreign_key raises NotImplementedError outright, confirmed by the SQLite migration
    # smoke test). An explicit constraint name is required too -- op.create_foreign_key(None, ...)
    # produces an unnamed constraint that op.drop_constraint(None, ...) then can't resolve on
    # ANY dialect, Postgres included (confirmed by actually running the downgrade).
    with op.batch_alter_table('quote_lines') as batch_op:
        batch_op.add_column(sa.Column('product_id', sa.Uuid(), nullable=True))
        batch_op.create_foreign_key('fk_quote_lines_product_id', 'products', ['product_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('quote_lines') as batch_op:
        batch_op.drop_constraint('fk_quote_lines_product_id', type_='foreignkey')
        batch_op.drop_column('product_id')
