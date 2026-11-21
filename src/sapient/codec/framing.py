"""Four-byte little-endian stream framing required by BSI Flex 335."""

import struct

from sapient.errors import FramingError

DEFAULT_MAX_MESSAGE_SIZE = 16 * 1024 * 1024
_HEADER = struct.Struct("<I")


def frame_payload(payload: bytes, *, max_size: int = DEFAULT_MAX_MESSAGE_SIZE) -> bytes:
    size = len(payload)
    if size == 0:
        raise FramingError("A SAPIENT frame cannot be empty")
    if size > max_size:
        raise FramingError(f"Frame size {size} exceeds limit {max_size}")
    return _HEADER.pack(size) + payload


class FrameDecoder:
    """Incrementally extract payloads from arbitrary byte-stream chunks."""

    def __init__(self, *, max_size: int = DEFAULT_MAX_MESSAGE_SIZE) -> None:
        self.max_size = max_size
        self._buffer = bytearray()

    def feed(self, data: bytes) -> list[bytes]:
        self._buffer.extend(data)
        frames: list[bytes] = []
        while len(self._buffer) >= _HEADER.size:
            (size,) = _HEADER.unpack_from(self._buffer)
            if size == 0:
                raise FramingError("A SAPIENT frame cannot be empty")
            if size > self.max_size:
                raise FramingError(f"Frame size {size} exceeds limit {self.max_size}")
            end = _HEADER.size + size
            if len(self._buffer) < end:
                break
            frames.append(bytes(self._buffer[_HEADER.size:end]))
            del self._buffer[:end]
        return frames

    @property
    def pending_bytes(self) -> int:
        return len(self._buffer)
