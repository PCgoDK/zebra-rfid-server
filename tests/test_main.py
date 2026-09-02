from fastapi import HTTPException
from datetime import datetime, timezone
from pathlib import Path
import pytest
from starlette.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api as api_module
from app.api import ReaderCreate, TagReadCreate, TagReadResponse, UserCreate, UserUpdate, create_api
from app.auth import DUMMY_PASSWORD_HASH, decode_access_token, hash_password
from app.config import Settings
from app.database import Base
from app.models import ApiUser, Reader, TagRead

TEST_SECRET = "a-secure-test-secret-with-at-least-32-bytes"


def create_test_session_factory() -> sessionmaker:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def get_route_endpoint(app, path: str):
    return next(route.endpoint for route in app.routes if route.path == path)


def test_health_endpoint_reports_service_status() -> None:
    app = create_api(Settings(jwt_secret=TEST_SECRET), create_test_session_factory())
    endpoint = get_route_endpoint(app, "/api/v1/health")
    response = endpoint()

    assert response == {"status": "ok"}


def test_dashboard_renders_login_and_reader_controls() -> None:
    app = create_api(Settings(jwt_secret=TEST_SECRET), create_test_session_factory())
    dashboard = get_route_endpoint(app, "/")
    response = dashboard(Request({"type": "http", "method": "GET", "path": "/", "headers": []}))

    body = response.body.decode()
    assert "Log ind" in body
    assert "Reader dashboard" in body
    assert "Åbn læser" in body
    assert "FXR90" in body
    assert "ST5500" in body
    assert 'id="home"' in body
    assert 'id="swagger"' in body
    assert 'id="swagger-panel"' in body
    assert 'id="swagger-frame"' in body
    assert 'src="/docs"' in body
    assert 'preauthorizeApiKey("HTTPBearer", token)' in body


def test_readme_describes_current_reader_event_contract() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "Konfiguration af RFID-laeser" in readme
    assert "newline-afgraenset JSON" in readme
    assert "Native LLRP/Zebra Event-konfiguration" in readme


def test_login_returns_a_token_only_for_valid_credentials() -> None:
    session_factory = create_test_session_factory()
    app = create_api(Settings(jwt_secret=TEST_SECRET), session_factory)
    login = get_route_endpoint(app, "/api/v1/auth/login")
    with session_factory() as session:
        session.add(ApiUser(username="admin", password_hash=hash_password("password")))
        session.commit()
        request = Request({"type": "http", "client": ("127.0.0.1", 12345)})
        payload_type = login.__annotations__["payload"]
        response = login(payload_type(username="admin", password="password"), request, session)

        assert decode_access_token(response.access_token, TEST_SECRET)["username"] == "admin"
        with pytest.raises(HTTPException, match="Invalid username or password"):
            login(payload_type(username="admin", password="wrong"), request, session)


def test_login_verifies_unknown_users_against_dummy_hash(monkeypatch) -> None:
    session_factory = create_test_session_factory()
    app = create_api(Settings(jwt_secret=TEST_SECRET), session_factory)
    login = get_route_endpoint(app, "/api/v1/auth/login")
    verified_hashes = []

    def verify_password(password_hash: str, password: str) -> bool:
        verified_hashes.append(password_hash)
        return False

    monkeypatch.setattr(api_module, "verify_password", verify_password)
    with session_factory() as session:
        request = Request({"type": "http", "client": ("127.0.0.1", 12345)})
        payload_type = login.__annotations__["payload"]
        with pytest.raises(HTTPException, match="Invalid username or password"):
            login(payload_type(username="missing", password="wrong"), request, session)

    assert verified_hashes == [DUMMY_PASSWORD_HASH]


def test_reader_creation_input_requires_a_safe_ipv4_address() -> None:
    assert ReaderCreate(name="Dock 1", ip_address="192.168.1.20").ip_address == "192.168.1.20"
    with pytest.raises(ValueError):
        ReaderCreate(name="Bad reader", ip_address="::1")


def test_reader_creation_accepts_optional_identification_details() -> None:
    reader = ReaderCreate(
        name="Dock 1",
        ip_address="192.168.1.20",
        serial_number="FX9600-123",
        mac_address="00:11:22:33:44:55",
        firmware_version="3.0.0",
    )

    assert reader.mac_address == "00:11:22:33:44:55"
    with pytest.raises(ValueError):
        ReaderCreate(name="Dock 1", ip_address="192.168.1.20", mac_address="invalid")


def test_reader_list_includes_received_tag_read_count() -> None:
    session_factory = create_test_session_factory()
    app = create_api(Settings(jwt_secret=TEST_SECRET), session_factory)
    list_readers = get_route_endpoint(app, "/api/v1/readers")
    now = datetime.now(timezone.utc)
    with session_factory() as session:
        reader = Reader(name="Dock 1", ip_address="192.168.1.20", status="receiving_data")
        session.add(reader)
        session.commit()
        session.add(
            TagRead(
                id=1,
                reader_id=reader.id,
                reader_ip=reader.ip_address,
                epc_hex="00AA",
                epc_decimal="170",
                epc_bit_length=16,
                antenna=1,
                rssi=-42,
                received_at=now,
                first_seen_at=now,
                last_seen_at=now,
                seen_count=1,
                raw_payload="{}",
                parse_status="valid",
            )
        )
        session.commit()

        readers = list_readers(offset=0, limit=100, session=session)

    assert readers[0].tag_read_count == 1


def test_tag_read_schemas_support_optional_st5500_fields() -> None:
    payload = TagReadCreate(
        reader_id=1,
        epc_hex="00AA",
        direction="inbound",
        zone="dock-1",
        location="north",
    )
    tag_read = TagRead(
        id=1,
        reader_id=1,
        reader_ip="192.0.2.10",
        epc_hex="00AA",
        epc_decimal="170",
        epc_bit_length=16,
        antenna=1,
        rssi=-42,
        received_at=datetime.now(timezone.utc),
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
        seen_count=1,
        raw_payload="{}",
        parse_status="valid",
    )

    assert payload.direction == "inbound"
    assert payload.zone == "dock-1"
    assert payload.location == "north"
    assert TagReadResponse.model_validate(tag_read).direction is None
    assert TagReadResponse.model_validate(tag_read).zone is None
    assert TagReadResponse.model_validate(tag_read).location is None


def test_tag_read_schemas_support_optional_fxr90_gps_fields() -> None:
    payload = TagReadCreate(
        reader_id=1,
        epc_hex="00AA",
        gps_latitude=55.6761,
        gps_longitude=12.5683,
        gps_altitude=14.5,
        gps_accuracy=3.2,
        gps_timestamp="2026-09-02T12:00:00Z",
    )

    assert payload.gps_latitude == 55.6761
    assert payload.gps_longitude == 12.5683
    assert payload.gps_timestamp.isoformat() == "2026-09-02T12:00:00+00:00"
    with pytest.raises(ValueError):
        TagReadCreate(reader_id=1, epc_hex="00AA", gps_latitude=91)


def test_user_update_requires_a_change_and_a_long_new_password() -> None:
    assert UserUpdate(current_password="current", username="new-admin").has_changes() is True
    assert UserUpdate(current_password="current").has_changes() is False
    with pytest.raises(ValueError):
        UserUpdate(current_password="current", new_password="too-short")


def test_admin_username_is_not_editable_in_portal_template() -> None:
    template = (Path("app/templates/dashboard.html")).read_text(encoding="utf-8")

    assert 'id="new-username"' not in template
    assert "Brugernavnet admin er fast" in template


def test_portal_exposes_administrator_api_user_creation() -> None:
    template = Path("app/templates/dashboard.html").read_text(encoding="utf-8")

    assert "Opret API-bruger" in template
    assert 'id="api-password"' in template
    assert 'value="api_client"' in template


def test_portal_escapes_dynamic_table_content() -> None:
    template = Path("app/templates/dashboard.html").read_text(encoding="utf-8")

    assert "function escapeHtml(value)" in template
    assert "${escapeHtml(user.username)}" in template
    assert "${escapeHtml(reader.name)}" in template


def test_user_creation_requires_a_valid_role_and_long_password() -> None:
    assert UserCreate(username="reader", password="long-enough-password", role="read_only").role == "read_only"
    with pytest.raises(ValueError):
        UserCreate(username="reader", password="too-short", role="owner")


def test_required_reader_and_tag_read_routes_are_registered() -> None:
    app = create_api(Settings(jwt_secret=TEST_SECRET), create_test_session_factory())
    routes = {(route.path, method) for route in app.routes for method in route.methods}

    assert {
        ("/api/v1/readers", "GET"),
        ("/api/v1/readers", "POST"),
        ("/api/v1/readers/{reader_id}", "GET"),
        ("/api/v1/readers/{reader_id}", "PATCH"),
        ("/api/v1/readers/discover", "POST"),
        ("/api/v1/auth/me", "PATCH"),
        ("/api/v1/users", "POST"),
        ("/api/v1/users", "GET"),
        ("/api/v1/users/{user_id}", "DELETE"),
        ("/api/v1/tag-reads", "GET"),
        ("/api/v1/tag-reads", "POST"),
        ("/api/v1/tag-reads/latest", "GET"),
        ("/api/v1/tag-reads/{tag_read_id}", "GET"),
    }.issubset(routes)
