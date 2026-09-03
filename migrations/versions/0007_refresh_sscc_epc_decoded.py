"""Refresh stored SSCC decoded values.

Revision ID: 0007_refresh_sscc_decoded
Revises: 0006_backfill_epc_decoded
"""

from alembic import op
import sqlalchemy as sa

from app.epc import decode_epc

revision = "0007_refresh_sscc_decoded"
down_revision = "0006_backfill_epc_decoded"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    tag_reads = connection.execute(sa.text("SELECT id, epc_hex FROM tag_reads"))
    for tag_read_id, epc_hex in tag_reads:
        decoded = decode_epc(epc_hex)
        if decoded is not None:
            connection.execute(
                sa.text("UPDATE tag_reads SET epc_decoded = :decoded WHERE id = :id"),
                {"decoded": decoded, "id": tag_read_id},
            )


def downgrade() -> None:
    pass