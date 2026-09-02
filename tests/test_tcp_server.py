import asyncio

from app.tcp_server import TcpReceiver


def test_tcp_receiver_handles_fragmented_and_combined_events() -> None:
    async def scenario() -> None:
        received = []

        async def collect(tag_read) -> None:
            received.append(tag_read)

        receiver = TcpReceiver("127.0.0.1", 0, 1000, collect)
        server = await receiver.start()
        port = server.sockets[0].getsockname()[1]
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        del reader
        first = b'{"reader_id": 1, "epc_hex": "00AA", "antenna": 1}'
        writer.write(first[:12])
        await writer.drain()
        writer.write(first[12:] + b'\n{"reader_id": 2, "epc_hex": "00BB", "antenna": 2}\n')
        await writer.drain()
        writer.close()
        await writer.wait_closed()
        await asyncio.sleep(0.01)
        server.close()
        await server.wait_closed()

        assert [item.event.epc_hex for item in received] == ["00AA", "00BB"]

    asyncio.run(scenario())