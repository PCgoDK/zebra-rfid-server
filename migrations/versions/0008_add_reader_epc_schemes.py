"""Add per-reader EPC scheme filters.

Revision ID: 0008_add_reader_epc_schemes
Revises: 0007_refresh_sscc_decoded
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_add_reader_epc_schemes"
down_revision = "0007_refresh_sscc_decoded"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("readers", sa.Column("epc_schemes", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("readers", "epc_schemes")