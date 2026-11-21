"""Asyncio TCP implementation of the SAPIENT framed connection."""

import asyncio
import ssl
import struct

from sapient.codec.framing import DEFAULT_MAX_MESSAGE_SIZE
from sapient.errors import ConnectionClosedError, EndOfStream, FramingError

_HEADER = struct.Struct("<I")


class TcpConnection:
    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        *,
        max_message_size: int = DEFAULT_MAX_MESSAGE_SIZE,
    ) -> None:
        self._reader = reader
        self._writer = writer
        self.max_message_size = max_message_size
        self._write_lock = asyncio.Lock()
        self._closed = False

    async def send_payload(self, payload: bytes) -> None:
        size = len(payload)
        if size == 0 or size > self.max_message_size:
            raise FramingError(f"Invalid outgoing frame size: {size}")
        async with self._write_lock:
            self._writer.write(_HEADER.pack(size) + payload)
            await self._writer.drain()

    async def receive_payload(self) -> bytes:
        try:
            header = await self._reader.readexactly(_HEADER.size)
        except asyncio.IncompleteReadError as exc:
            if not exc.partial:
                raise EndOfStream("TCP peer closed between SAPIENT frames") from exc
            raise ConnectionClosedError("TCP stream closed during a frame header") from exc
        (size,) = _HEADER.unpack(header)
        if size == 0 or size > self.max_message_size:
            raise FramingError(f"Invalid incoming frame size: {size}")
        try:
            return await self._reader.readexactly(size)
        except asyncio.IncompleteReadError as exc:
            raise ConnectionClosedError("TCP stream closed during a frame payload") from exc

    async def close(self, *, timeout: float = 1) -> None:
        if self._closed:
            return
        self._closed = True
        self._writer.close()
        try:
            await asyncio.wait_for(self._writer.wait_closed(), timeout)
        except (TimeoutError, ConnectionError):
            transport = getattr(self._writer, "transport", None)
            if transport is not None:
                transport.abort()

    @property
    def peername(self):
        return self._writer.get_extra_info("peername")


async def open_tcp_connection(
    host: str,
    port: int,
    *,
    max_message_size: int = DEFAULT_MAX_MESSAGE_SIZE,
    ssl_context: ssl.SSLContext | None = None,
    server_hostname: str | None = None,
) -> TcpConnection:
    reader, writer = await asyncio.open_connection(
        host,
        port,
        ssl=ssl_context,
        server_hostname=server_hostname,
    )
    return TcpConnection(reader, writer, max_message_size=max_message_size)
