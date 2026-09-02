"""Add optional FXR90 GPS fields.

Revision ID: 0003_add_fxr90_gps_fields
Revises: 0002_add_st5500_optional_fields
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_add_fxr90_gps_fields"
down_revision = "0002_add_st5500_optional_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tag_reads", sa.Column("gps_latitude", sa.Float(), nullable=True))
    op.add_column("tag_reads", sa.Column("gps_longitude", sa.Float(), nullable=True))
    op.add_column("tag_reads", sa.Column("gps_altitude", sa.Float(), nullable=True))
    op.add_column("tag_reads", sa.Column("gps_accuracy", sa.Float(), nullable=True))
    op.add_column("tag_reads", sa.Column("gps_timestamp", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("tag_reads", "gps_timestamp")
    op.drop_column("tag_reads", "gps_accuracy")
    op.drop_column("tag_reads", "gps_altitude")
    op.drop_column("tag_reads", "gps_longitude")
    op.drop_column("tag_reads", "gps_latitude")