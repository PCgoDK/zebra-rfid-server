from collections.abc import Callable, Iterator
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path

from app.rfid import AggregatedTagRead, TagEvent


class EventBuffer:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, tag_read: AggregatedTagRead) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as buffer_file:
            buffer_file.write(json.dumps(self._serialize(tag_read), separators=(",", ":")) + "\n")

    def replay(self, save: Callable[[AggregatedTagRead], object]) -> int:
        if not self.path.exists():
            return 0
        replayed = 0
        lines = self.path.read_text(encoding="utf-8").splitlines()
        remaining: list[str] = []
        for index, line in enumerate(lines):
            try:
                save(self._deserialize(json.loads(line)))
                replayed += 1
            except Exception:
                remaining = lines[index:]
                break
        if remaining:
            self.path.write_text("\n".join(remaining) + "\n", encoding="utf-8")
        else:
            self.path.unlink(missing_ok=True)
        return replayed

    @staticmethod
    def _serialize(tag_read: AggregatedTagRead) -> dict[str, object]:
        data = asdict(tag_read)
        event = data["event"]
        assert isinstance(event, dict)
        for key in ("reader_timestamp",):
            if event[key] is not None:
                event[key] = event[key].isoformat()
        for key in ("first_seen_at", "last_seen_at"):
            data[key] = data[key].isoformat()
        return data

    @staticmethod
    def _deserialize(data: dict[str, object]) -> AggregatedTagRead:
        event_data = dict(data["event"])
        if event_data["reader_timestamp"] is not None:
            event_data["reader_timestamp"] = datetime.fromisoformat(event_data["reader_timestamp"])
        return AggregatedTagRead(
            event=TagEvent(**event_data),
            first_seen_at=datetime.fromisoformat(data["first_seen_at"]),
            last_seen_at=datetime.fromisoformat(data["last_seen_at"]),
            seen_count=data["seen_count"],
            is_duplicate=data["is_duplicate"],
        )