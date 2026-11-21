"""Generic message receiver and asynchronous iterator."""

from sapient.codec import decode_message
from sapient.errors import EndOfStream
from sapient.transports.base import MessageConnection
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage


class SapientReceiver:
    def __init__(self, connection: MessageConnection, *, validate: bool = True) -> None:
        self.connection = connection
        self.validate = validate

    async def receive(self) -> SapientMessage:
        payload = await self.connection.receive_payload()
        return decode_message(payload, validate=self.validate)

    def __aiter__(self):
        return self

    async def __anext__(self) -> SapientMessage:
        try:
            return await self.receive()
        except EndOfStream:
            raise StopAsyncIteration from None
        except BaseException as exc:
            if isinstance(exc, GeneratorExit):
                raise
            # Cancellation or failure ends ownership of this receive loop.
            await self.connection.close()
            raise

    async def close(self) -> None:
        await self.connection.close()

    async def __aenter__(self) -> "SapientReceiver":
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.close()
