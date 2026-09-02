from datetime import datetime, timedelta, timezone

from app.rfid import DuplicateAggregator, TagEvent, parse_simulator_event


def test_parser_normalizes_epc_and_preserves_unknown_data() -> None:
    event = parse_simulator_event('{"reader_id": 4, "epc_hex": "00aa", "antenna": 2, "vendor": "zebra"}', "10.0.0.2")

    assert event.epc_hex == "00AA"
    assert event.reader_ip == "10.0.0.2"
    assert event.extra_data == {"vendor": "zebra"}


def test_parser_accepts_the_simulator_96_bit_epc_shape() -> None:
    event = parse_simulator_event(
        '{"reader_id": 1, "epc_hex": "31D55BE6800002156C000000", "antenna": 1}',
        "10.0.0.2",
    )

    assert len(event.epc_hex) == 24


def test_parser_extracts_optional_st5500_fields() -> None:
    event = parse_simulator_event(
        '{"reader_id": 4, "epc_hex": "00aa", "antenna": 2, "direction": "inbound", "zone": "dock-1", "location": "north"}',
        "10.0.0.2",
    )

    assert event.direction == "inbound"
    assert event.zone == "dock-1"
    assert event.location == "north"
    assert event.extra_data is None


def test_parser_extracts_optional_fxr90_gps_fields() -> None:
    event = parse_simulator_event(
        '{"reader_id": 4, "epc_hex": "00aa", "gps_latitude": 55.6761, "gps_longitude": 12.5683, "gps_altitude": 14.5, "gps_accuracy": 3.2, "gps_timestamp": "2026-09-02T12:00:00Z"}',
        "10.0.0.2",
    )

    assert event.gps_latitude == 55.6761
    assert event.gps_longitude == 12.5683
    assert event.gps_altitude == 14.5
    assert event.gps_accuracy == 3.2
    assert event.gps_timestamp.isoformat() == "2026-09-02T12:00:00+00:00"
    assert event.extra_data is None


def test_duplicate_aggregator_updates_existing_read_inside_window() -> None:
    aggregator = DuplicateAggregator(window_ms=1000)
    event = TagEvent(1, "00AA", 2, "10.0.0.2", rssi=-50)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    first = aggregator.process(event, now)
    duplicate = aggregator.process(TagEvent(1, "00AA", 2, "10.0.0.2", rssi=-42), now + timedelta(milliseconds=999))

    assert first.is_duplicate is False
    assert duplicate.is_duplicate is True
    assert duplicate.seen_count == 2
    assert duplicate.event.rssi == -42


def test_duplicate_aggregator_creates_new_read_outside_window() -> None:
    aggregator = DuplicateAggregator(window_ms=1000)
    event = TagEvent(1, "00AA", 2, "10.0.0.2")
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    aggregator.process(event, now)
    later = aggregator.process(event, now + timedelta(milliseconds=1001))

    assert later.is_duplicate is False
    assert later.seen_count == 1