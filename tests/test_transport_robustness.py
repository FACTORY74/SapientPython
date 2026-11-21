import asyncio
import struct

import pytest

from sapient.codec import FrameDecoder, frame_payload
from sapient.codec import encode_message
from sapient.errors import ConnectionClosedError, EndOfStream, FramingError
from sapient.endpoints import SapientReceiver
from sapient.roles import FusionNodeServer
from sapient.transports.tcp import TcpConnection, open_tcp_connection
from sapient.messages import create_message
from tests.factories import NODE_ID, status


class FakeWriter:
    def __init__(self) -> None:
        self.closed = False
        self.data = bytearray()

    def write(self, data: bytes) -> None:
        self.data.extend(data)

    async def drain(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        pass

    def get_extra_info(self, name: str):
        return None


def connection_with(data: bytes, *, eof: bool = True):
    reader = asyncio.StreamReader()
    reader.feed_data(data)
    if eof:
        reader.feed_eof()
    writer = FakeWriter()
    return TcpConnection(reader, writer), writer


def test_empty_oversized_and_fragmented_frames() -> None:
    with pytest.raises(FramingError, match="empty"):
        frame_payload(b"")
    with pytest.raises(FramingError, match="exceeds"):
        frame_payload(b"ab", max_size=1)
    decoder = FrameDecoder(max_size=10)
    framed = frame_payload(b"abc")
    assert decoder.feed(framed[:2]) == []
    assert decoder.feed(framed[2:5]) == []
    assert decoder.feed(framed[5:]) == [b"abc"]
    with pytest.raises(FramingError, match="exceeds"):
        FrameDecoder(max_size=1).feed(struct.pack("<I", 2))


def test_clean_eof_and_truncated_frames_are_distinct() -> None:
    async def scenario() -> None:
        clean, _ = connection_with(b"")
        with pytest.raises(EndOfStream):
            await clean.receive_payload()
        header, _ = connection_with(b"\x03\x00")
        with pytest.raises(ConnectionClosedError, match="header"):
            await header.receive_payload()
        payload, _ = connection_with(struct.pack("<I", 4) + b"ab")
        with pytest.raises(ConnectionClosedError, match="payload"):
            await payload.receive_payload()

    asyncio.run(scenario())


def test_receiver_iteration_stops_at_eof_and_cancellation_closes_connection() -> None:
    async def scenario() -> None:
        connection, _ = connection_with(b"")
        received = [message async for message in SapientReceiver(connection)]
        assert received == []

        waiting, writer = connection_with(b"", eof=False)
        receiver = SapientReceiver(waiting)
        task = asyncio.create_task(receiver.__anext__())
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert writer.closed

    asyncio.run(scenario())


def test_server_tracks_concurrent_clients_and_closes_them() -> None:
    async def scenario() -> None:
        async def handler(message, sender) -> None:
            pass

        server = await FusionNodeServer.start("127.0.0.1", 0, handler)
        first = await open_tcp_connection("127.0.0.1", server.port)
        second = await open_tcp_connection("127.0.0.1", server.port)
        for _ in range(100):
            if server.active_connection_count == 2:
                break
            await asyncio.sleep(0.001)
        assert server.active_connection_count == 2
        await asyncio.wait_for(server.close(timeout=1), 3)
        with pytest.raises(EndOfStream):
            await asyncio.wait_for(first.receive_payload(), 1)
        with pytest.raises(EndOfStream):
            await asyncio.wait_for(second.receive_payload(), 1)

    asyncio.run(scenario())


def test_handler_failures_are_observable() -> None:
    async def scenario() -> None:
        failed = asyncio.Event()

        def on_error(exc: BaseException) -> None:
            failed.set()

        async def handler(message, sender) -> None:
            raise RuntimeError("handler failed")

        server = await FusionNodeServer.start(
            "127.0.0.1", 0, handler, error_handler=on_error
        )
        connection = await open_tcp_connection("127.0.0.1", server.port)
        try:
            await connection.send_payload(
                encode_message(create_message(sender_id=NODE_ID, content=status()))
            )
            await asyncio.wait_for(failed.wait(), 1)
            assert server.errors
            assert isinstance(server.errors[0], RuntimeError)
        finally:
            await connection.close()
            await server.close()

    asyncio.run(scenario())


def test_invalid_protobuf_is_observable() -> None:
    async def scenario() -> None:
        failed = asyncio.Event()

        async def handler(message, sender) -> None:
            pass

        server = await FusionNodeServer.start(
            "127.0.0.1", 0, handler, error_handler=lambda exc: failed.set()
        )
        connection = await open_tcp_connection("127.0.0.1", server.port)
        try:
            await connection.send_payload(b"\x00")
            await asyncio.wait_for(failed.wait(), 1)
            assert server.errors
        finally:
            await connection.close()
            await server.close()

    asyncio.run(scenario())
