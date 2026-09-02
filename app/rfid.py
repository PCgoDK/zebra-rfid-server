from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
from typing import Any

from app.epc import parse_epc


@dataclass(frozen=True)
class TagEvent:
    reader_id: int
    epc_hex: str
    antenna: int | None
    reader_ip: str
    rssi: float | None = None
    phase: float | None = None
    channel: int | None = None
    direction: str | None = None
    zone: str | None = None
    location: str | None = None
    reader_timestamp: datetime | None = None
    raw_payload: str = ""
    extra_data: dict[str, Any] | None = None


@dataclass(frozen=True)
class AggregatedTagRead:
    event: TagEvent
    first_seen_at: datetime
    last_seen_at: datetime
    seen_count: int
    is_duplicate: bool


def parse_simulator_event(payload: str, reader_ip: str) -> TagEvent:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as error:
        raise ValueError("Payload must be valid JSON") from error

    try:
        reader_id = int(data["reader_id"])
        antenna = int(data["antenna"]) if data.get("antenna") is not None else None
        epc = parse_epc(str(data["epc_hex"]))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Payload requires reader_id and hexadecimal epc_hex") from error

    known_fields = {
        "reader_id", "epc_hex", "antenna", "rssi", "phase", "channel", "direction", "zone", "location"
    }
    return TagEvent(
        reader_id=reader_id,
        epc_hex=epc.hex_value,
        antenna=antenna,
        reader_ip=reader_ip,
        rssi=float(data["rssi"]) if data.get("rssi") is not None else None,
        phase=float(data["phase"]) if data.get("phase") is not None else None,
        channel=int(data["channel"]) if data.get("channel") is not None else None,
        direction=str(data["direction"]) if data.get("direction") is not None else None,
        zone=str(data["zone"]) if data.get("zone") is not None else None,
        location=str(data["location"]) if data.get("location") is not None else None,
        raw_payload=payload,
        extra_data={key: value for key, value in data.items() if key not in known_fields} or None,
    )


class DuplicateAggregator:
    def __init__(self, window_ms: int) -> None:
        self.window_seconds = window_ms / 1000
        self._reads: dict[tuple[int, str, int | None], AggregatedTagRead] = {}

    def process(self, event: TagEvent, received_at: datetime | None = None) -> AggregatedTagRead:
        received_at = received_at or datetime.now(timezone.utc)
        key = (event.reader_id, event.epc_hex, event.antenna)
        existing = self._reads.get(key)
        if existing and (received_at - existing.last_seen_at).total_seconds() * 1000 <= self.window_seconds * 1000:
            aggregated = replace(
                existing,
                event=event,
                last_seen_at=received_at,
                seen_count=existing.seen_count + 1,
                is_duplicate=True,
            )
        else:
            aggregated = AggregatedTagRead(event, received_at, received_at, 1, False)
        self._reads[key] = aggregated
        return aggregated