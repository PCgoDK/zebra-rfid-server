"""Send provisional newline-delimited JSON RFID events to a TCP receiver."""

import argparse
import asyncio
import json
from collections.abc import Sequence


def parse_epcs(value: str) -> list[str]:
    epcs = [epc.strip().upper().removeprefix("0X") for epc in value.split(",") if epc.strip()]
    if not epcs or any(len(epc) % 2 or any(character not in "0123456789ABCDEF" for character in epc) for epc in epcs):
        raise argparse.ArgumentTypeError("EPCs must contain complete hexadecimal bytes")
    return epcs


def event_payload(reader_id: int, sequence: int, epcs: Sequence[str], antennas: int, duplicates: int) -> bytes:
    unique_sequence = sequence // (duplicates + 1)
    event = {
        "reader_id": reader_id,
        "epc_hex": epcs[unique_sequence % len(epcs)],
        "antenna": unique_sequence % antennas + 1,
        "rssi": -45.0 - (sequence % 10),
        "phase": float((sequence * 15) % 360),
        "channel": sequence % 4 + 1,
    }
    return (json.dumps(event, separators=(",", ":")) + "\n").encode()


async def send_events(
    host: str,
    port: int,
    reader_id: int,
    event_count: int,
    fragment: bool,
    epcs: Sequence[str],
    antennas: int,
    duplicates: int,
    disconnect_every: int,
    interval_ms: int,
) -> None:
    writer: asyncio.StreamWriter | None = None
    try:
        for sequence in range(event_count):
            if writer is None:
                _, writer = await asyncio.open_connection(host, port)
            encoded = event_payload(reader_id, sequence, epcs, antennas, duplicates)
            if fragment:
                midpoint = len(encoded) // 2
                writer.write(encoded[:midpoint])
                await writer.drain()
                writer.write(encoded[midpoint:])
            else:
                writer.write(encoded)
            await writer.drain()
            if disconnect_every and (sequence + 1) % disconnect_every == 0:
                writer.close()
                await writer.wait_closed()
                writer = None
            if interval_ms:
                await asyncio.sleep(interval_ms / 1000)
    finally:
        if writer is not None:
            writer.close()
            await writer.wait_closed()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5084)
    parser.add_argument("--readers", type=int, default=2)
    parser.add_argument("--events", type=int, default=10)
    parser.add_argument("--fragment", action="store_true")
    parser.add_argument("--epcs", type=parse_epcs, default=parse_epcs("31D55BE6800002156C000000,31D55BE6800002156C000001"))
    parser.add_argument("--antennas", type=int, default=4)
    parser.add_argument("--duplicates", type=int, default=0)
    parser.add_argument("--disconnect-every", type=int, default=0)
    parser.add_argument("--interval-ms", type=int, default=0)
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if args.port not in range(1, 65536):
        raise ValueError("port must be between 1 and 65535")
    if args.readers < 1 or args.events < 1 or args.antennas < 1:
        raise ValueError("readers, events, and antennas must be at least 1")
    if args.duplicates < 0 or args.disconnect_every < 0 or args.interval_ms < 0:
        raise ValueError("duplicates, disconnect-every, and interval-ms must not be negative")
    await asyncio.gather(
        *(
            send_events(
                args.host,
                args.port,
                reader_id,
                args.events,
                args.fragment,
                args.epcs,
                args.antennas,
                args.duplicates,
                args.disconnect_every,
                args.interval_ms,
            )
            for reader_id in range(1, args.readers + 1)
        )
    )


if __name__ == "__main__":
    asyncio.run(main())