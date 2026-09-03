from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.epc import decode_epc, epc_scheme_is_allowed, parse_epc
from app.models import Reader, TagRead
from app.rfid import AggregatedTagRead


class TagReadRepository:
    def __init__(self, session_factory: sessionmaker[Session], duplicate_window_ms: int) -> None:
        self.session_factory = session_factory
        self.duplicate_window = timedelta(milliseconds=duplicate_window_ms)

    def save(self, aggregated: AggregatedTagRead) -> TagRead | None:
        event = aggregated.event
        epc = parse_epc(event.epc_hex)
        with self.session_factory() as session:
            reader = session.get(Reader, event.reader_id)
            if reader is None:
                raise ValueError(f"Reader {event.reader_id} is not registered")
            if not epc_scheme_is_allowed(epc.hex_value, reader.epc_schemes):
                return None

            reader.last_seen_at = aggregated.last_seen_at
            reader.last_data_at = aggregated.last_seen_at
            reader.status = "receiving_data"
            existing = session.scalar(
                select(TagRead)
                .where(
                    TagRead.reader_id == event.reader_id,
                    TagRead.epc_hex == epc.hex_value,
                    TagRead.antenna == event.antenna,
                    TagRead.last_seen_at >= aggregated.last_seen_at - self.duplicate_window,
                )
                .order_by(TagRead.last_seen_at.desc())
                .limit(1)
            )
            if existing is not None:
                existing.last_seen_at = aggregated.last_seen_at
                existing.seen_count += 1
                existing.epc_decoded = decode_epc(epc.hex_value)
                existing.rssi = event.rssi
                existing.phase = event.phase
                existing.channel = event.channel
                existing.direction = event.direction
                existing.zone = event.zone
                existing.location = event.location
                existing.gps_latitude = event.gps_latitude
                existing.gps_longitude = event.gps_longitude
                existing.gps_altitude = event.gps_altitude
                existing.gps_accuracy = event.gps_accuracy
                existing.gps_timestamp = event.gps_timestamp
                existing.reader_timestamp = event.reader_timestamp
                existing.raw_payload = event.raw_payload
                existing.extra_data = event.extra_data
                tag_read = existing
            else:
                tag_read = TagRead(
                    reader_id=event.reader_id,
                    reader_ip=event.reader_ip,
                    epc_hex=epc.hex_value,
                    epc_decoded=decode_epc(epc.hex_value),
                    epc_bit_length=epc.bit_length,
                    antenna=event.antenna,
                    rssi=event.rssi,
                    phase=event.phase,
                    channel=event.channel,
                    direction=event.direction,
                    zone=event.zone,
                    location=event.location,
                    gps_latitude=event.gps_latitude,
                    gps_longitude=event.gps_longitude,
                    gps_altitude=event.gps_altitude,
                    gps_accuracy=event.gps_accuracy,
                    gps_timestamp=event.gps_timestamp,
                    reader_timestamp=event.reader_timestamp,
                    received_at=aggregated.last_seen_at,
                    first_seen_at=aggregated.first_seen_at,
                    last_seen_at=aggregated.last_seen_at,
                    seen_count=aggregated.seen_count,
                    raw_payload=event.raw_payload,
                    extra_data=event.extra_data,
                    parse_status="valid",
                )
                session.add(tag_read)
            session.commit()
            session.refresh(tag_read)
            return tag_read