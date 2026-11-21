"""Minimal in-memory implementation of the MessageConnection protocol."""

import asyncio

from sapient.endpoints import SapientReceiver, SapientSender
from sapient.messages import create_message
from _fixtures import NODE_ID, status


class MemoryConnection:
    def __init__(self) -> None:
        self.payloads: asyncio.Queue[bytes] = asyncio.Queue()

    async def send_payload(self, payload: bytes) -> None:
        await self.payloads.put(payload)

    async def receive_payload(self) -> bytes:
        return await self.payloads.get()

    async def close(self) -> None:
        pass


async def main() -> None:
    connection = MemoryConnection()
    await SapientSender(connection).send(
        create_message(sender_id=NODE_ID, content=status())
    )
    message = await SapientReceiver(connection).receive()
    print(message.WhichOneof("content"))


if __name__ == "__main__":
    asyncio.run(main())
