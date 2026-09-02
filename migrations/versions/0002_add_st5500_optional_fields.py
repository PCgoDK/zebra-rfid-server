"""Add optional ST5500 tag read fields.

Revision ID: 0002_add_st5500_optional_fields
Revises: 0001_initial_schema
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_st5500_optional_fields"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tag_reads", sa.Column("direction", sa.String(length=64), nullable=True))
    op.add_column("tag_reads", sa.Column("zone", sa.String(length=255), nullable=True))
    op.add_column("tag_reads", sa.Column("location", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("tag_reads", "location")
    op.drop_column("tag_reads", "zone")
    op.drop_column("tag_reads", "direction")