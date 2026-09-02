from datetime import datetime, timezone

from app.buffer import EventBuffer
from app.rfid import AggregatedTagRead, TagEvent


def sample_tag_read() -> AggregatedTagRead:
    event = TagEvent(1, "00AA", 1, "192.168.1.20", rssi=-42, raw_payload="{}")
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return AggregatedTagRead(event, now, now, 1, False)


def test_buffer_replays_and_removes_events_after_success(tmp_path) -> None:
    buffer = EventBuffer(tmp_path / "events.jsonl")
    buffer.append(sample_tag_read())
    replayed = []

    assert buffer.replay(replayed.append) == 1
    assert replayed[0].event.epc_hex == "00AA"
    assert buffer.path.exists() is False


def test_buffer_keeps_failed_event_for_later_retry(tmp_path) -> None:
    buffer = EventBuffer(tmp_path / "events.jsonl")
    buffer.append(sample_tag_read())
    buffer.append(sample_tag_read())

    assert buffer.replay(lambda _: (_ for _ in ()).throw(ConnectionError())) == 0
    assert len(buffer.path.read_text(encoding="utf-8").splitlines()) == 2