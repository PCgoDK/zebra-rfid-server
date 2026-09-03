"""Backfill complete decoded EPC values.

Revision ID: 0006_backfill_epc_decoded
Revises: 0005_add_epc_decoded
"""

from alembic import op
import sqlalchemy as sa

from app.epc import decode_epc

revision = "0006_backfill_epc_decoded"
down_revision = "0005_add_epc_decoded"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    tag_reads = connection.execute(sa.text("SELECT id, epc_hex FROM tag_reads"))
    for tag_read_id, epc_hex in tag_reads:
        connection.execute(
            sa.text("UPDATE tag_reads SET epc_decoded = :decoded WHERE id = :id"),
            {"decoded": decode_epc(epc_hex), "id": tag_read_id},
        )


def downgrade() -> None:
    pass