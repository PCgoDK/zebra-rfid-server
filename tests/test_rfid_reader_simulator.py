import asyncio
import json

from tools.rfid_reader_simulator import send_events


def test_simulator_sends_fragmented_events_from_multiple_readers() -> None:
    async def scenario() -> None:
        received: list[dict[str, object]] = []
        complete = asyncio.Event()

        async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            try:
                while payload := await reader.readline():
                    received.append(json.loads(payload))
                    if len(received) == 8:
                        complete.set()
            finally:
                writer.close()
                await writer.wait_closed()

        server = await asyncio.start_server(handle_connection, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        try:
            await asyncio.gather(
                send_events("127.0.0.1", port, 1, 4, True, ["00AA", "00BB"], 2, 1, 2, 0),
                send_events("127.0.0.1", port, 2, 4, True, ["00AA", "00BB"], 2, 1, 2, 0),
            )
            await asyncio.wait_for(complete.wait(), timeout=1)
        finally:
            server.close()
            await server.wait_closed()

        assert {event["reader_id"] for event in received} == {1, 2}
        assert {event["epc_hex"] for event in received} == {"00AA", "00BB"}
        assert [event["epc_hex"] for event in received if event["reader_id"] == 1][:2] == ["00AA", "00AA"]

    asyncio.run(scenario())