"""Transport interface consumed by SAPIENT endpoints."""

from typing import Protocol


class MessageConnection(Protocol):
    async def send_payload(self, payload: bytes) -> None: ...

    async def receive_payload(self) -> bytes: ...

    async def close(self) -> None: ...
