"""Add decoded EPC storage.

Revision ID: 0005_add_epc_decoded
Revises: 0004_remove_epc_decimal
"""

from alembic import op
import sqlalchemy as sa

from app.epc import decode_epc

revision = "0005_add_epc_decoded"
down_revision = "0004_remove_epc_decimal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tag_reads", sa.Column("epc_decoded", sa.String(255), nullable=True))
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
    op.drop_column("tag_reads", "epc_decoded")