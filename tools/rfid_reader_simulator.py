"""Send provisional newline-delimited JSON RFID events to a TCP receiver."""

import argparse
import asyncio
import json
import random


async def send_events(host: str, port: int, reader_id: int, event_count: int, fragment: bool) -> None:
    reader, writer = await asyncio.open_connection(host, port)
    del reader
    for sequence in range(event_count):
        event = {
            "reader_id": reader_id,
            "epc_hex": f"31D55BE6800002156C{sequence % 16:06X}",
            "antenna": sequence % 4 + 1,
            "rssi": round(random.uniform(-70, -30), 1),
            "phase": round(random.uniform(0, 360), 1),
            "channel": 1,
        }
        encoded = (json.dumps(event) + "\n").encode()
        if fragment:
            midpoint = len(encoded) // 2
            writer.write(encoded[:midpoint])
            await writer.drain()
            writer.write(encoded[midpoint:])
        else:
            writer.write(encoded)
        await writer.drain()
    writer.close()
    await writer.wait_closed()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5084)
    parser.add_argument("--readers", type=int, default=2)
    parser.add_argument("--events", type=int, default=10)
    parser.add_argument("--fragment", action="store_true")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    await asyncio.gather(
        *(
            send_events(args.host, args.port, reader_id, args.events, args.fragment)
            for reader_id in range(1, args.readers + 1)
        )
    )


if __name__ == "__main__":
    asyncio.run(main())