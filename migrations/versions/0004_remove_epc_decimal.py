"""Remove unused decimal EPC storage.

Revision ID: 0004_remove_epc_decimal
Revises: 0003_add_fxr90_gps_fields
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_remove_epc_decimal"
down_revision = "0003_add_fxr90_gps_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_tag_reads_epc_decimal", table_name="tag_reads")
    op.drop_column("tag_reads", "epc_decimal")


def downgrade() -> None:
    op.add_column("tag_reads", sa.Column("epc_decimal", sa.String(128), nullable=True))
    op.execute("UPDATE tag_reads SET epc_decimal = '0'")
    op.alter_column("tag_reads", "epc_decimal", nullable=False)
    op.create_index("ix_tag_reads_epc_decimal", "tag_reads", ["epc_decimal"])