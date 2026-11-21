"""Generic message sender."""

from sapient.codec import encode_message
from sapient.transports.base import MessageConnection
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage


class SapientSender:
    def __init__(self, connection: MessageConnection, *, validate: bool = True) -> None:
        self.connection = connection
        self.validate = validate

    async def send(self, message: SapientMessage) -> None:
        await self.connection.send_payload(encode_message(message, validate=self.validate))
