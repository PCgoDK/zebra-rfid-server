"""Create the initial Zebra RFID Server schema.

Revision ID: 0001_initial_schema
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "readers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("ip_address", sa.String(45), nullable=False, unique=True),
        sa.Column("model", sa.String(100)),
        sa.Column("serial_number", sa.String(100), unique=True),
        sa.Column("mac_address", sa.String(17), unique=True),
        sa.Column("firmware_version", sa.String(100)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("last_data_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "api_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "application_settings",
        sa.Column("key", sa.String(255), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("value_type", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "tag_reads",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("reader_id", sa.Integer(), sa.ForeignKey("readers.id"), nullable=False),
        sa.Column("reader_ip", sa.String(45), nullable=False),
        sa.Column("epc_hex", sa.String(128), nullable=False),
        sa.Column("epc_decimal", sa.String(128), nullable=False),
        sa.Column("epc_bit_length", sa.Integer(), nullable=False),
        sa.Column("antenna", sa.Integer()), sa.Column("rssi", sa.Float()), sa.Column("phase", sa.Float()),
        sa.Column("channel", sa.Integer()), sa.Column("reader_timestamp", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("seen_count", sa.Integer(), nullable=False), sa.Column("raw_payload", sa.Text(), nullable=False),
        sa.Column("extra_data", sa.JSON()), sa.Column("parse_status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tag_reads_epc_hex", "tag_reads", ["epc_hex"])
    op.create_index("ix_tag_reads_epc_decimal", "tag_reads", ["epc_decimal"])
    op.create_index("ix_tag_reads_reader_received", "tag_reads", ["reader_id", "received_at"])
    op.create_index("ix_tag_reads_reader_id", "tag_reads", ["reader_id"])
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("api_users.id")),
        sa.Column("event_type", sa.String(100), nullable=False), sa.Column("source_ip", sa.String(45)),
        sa.Column("details", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("tag_reads")
    op.drop_table("application_settings")
    op.drop_table("api_users")
    op.drop_table("readers")