"""Create the initial database schema."""

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
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("ip_address", sa.String(length=45), nullable=False, unique=True),
        sa.Column("model", sa.String(length=100)),
        sa.Column("serial_number", sa.String(length=100), unique=True),
        sa.Column("mac_address", sa.String(length=17)),
        sa.Column("firmware_version", sa.String(length=100)),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("last_data_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_readers_ip_address", "readers", ["ip_address"])
    op.create_index("ix_readers_status", "readers", ["status"])
    op.create_index("ix_readers_last_seen_at", "readers", ["last_seen_at"])

    op.create_table(
        "tag_reads",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("reader_id", sa.Integer(), sa.ForeignKey("readers.id")),
        sa.Column("reader_ip", sa.String(length=45), nullable=False),
        sa.Column("epc_hex", sa.String(length=128), nullable=False),
        sa.Column("epc_decimal", sa.String(length=128), nullable=False),
        sa.Column("epc_bit_length", sa.Integer(), nullable=False),
        sa.Column("antenna", sa.Integer()),
        sa.Column("rssi", sa.Float()),
        sa.Column("phase", sa.Float()),
        sa.Column("channel", sa.Integer()),
        sa.Column("reader_timestamp", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("seen_count", sa.Integer(), nullable=False),
        sa.Column("raw_payload", sa.Text()),
        sa.Column("extra_data", sa.JSON()),
        sa.Column("parse_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for column in ("reader_id", "reader_ip", "epc_hex", "epc_decimal", "antenna"):
        op.create_index(f"ix_tag_reads_{column}", "tag_reads", [column])

    op.create_table(
        "api_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "application_settings",
        sa.Column("key", sa.String(length=255), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("value_type", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("api_users.id")),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("source_ip", sa.String(length=45)),
        sa.Column("details", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_event_type", "audit_log", ["event_type"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("application_settings")
    op.drop_table("api_users")
    op.drop_table("tag_reads")
    op.drop_table("readers")
