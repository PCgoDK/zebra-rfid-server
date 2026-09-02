"""Database models for Zebra RFID Server."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Reader(Timestamped, Base):
    __tablename__ = "readers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    ip_address: Mapped[str] = mapped_column(String(45), unique=True, index=True)
    model: Mapped[str | None] = mapped_column(String(100))
    serial_number: Mapped[str | None] = mapped_column(String(100), unique=True)
    mac_address: Mapped[str | None] = mapped_column(String(17))
    firmware_version: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_data_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class TagRead(Timestamped, Base):
    __tablename__ = "tag_reads"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    reader_id: Mapped[int | None] = mapped_column(ForeignKey("readers.id"), index=True)
    reader_ip: Mapped[str] = mapped_column(String(45), index=True)
    epc_hex: Mapped[str] = mapped_column(String(128), index=True)
    epc_decimal: Mapped[str] = mapped_column(String(128), index=True)
    epc_bit_length: Mapped[int] = mapped_column(Integer)
    antenna: Mapped[int | None] = mapped_column(Integer, index=True)
    rssi: Mapped[float | None] = mapped_column()
    phase: Mapped[float | None] = mapped_column()
    channel: Mapped[int | None] = mapped_column(Integer)
    reader_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    seen_count: Mapped[int] = mapped_column(Integer, default=1)
    raw_payload: Mapped[str | None] = mapped_column(Text)
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    parse_status: Mapped[str] = mapped_column(String(32), default="valid")


class ApiUser(Timestamped, Base):
    __tablename__ = "api_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[str] = mapped_column(String(32), default="administrator")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApplicationSetting(Base):
    __tablename__ = "application_settings"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    value_type: Mapped[str] = mapped_column(String(32))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("api_users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    source_ip: Mapped[str | None] = mapped_column(String(45))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
