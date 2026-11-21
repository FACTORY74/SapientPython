"""Encoding and decoding of complete SAPIENT envelopes."""

from google.protobuf.message import DecodeError
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage

from sapient.errors import CodecError
from sapient.validation import validate_message


def encode_message(message: SapientMessage, *, validate: bool = True) -> bytes:
    if not isinstance(message, SapientMessage):
        raise TypeError("message must be a SapientMessage")
    if validate:
        validate_message(message)
    return message.SerializeToString()


def decode_message(payload: bytes, *, validate: bool = True) -> SapientMessage:
    message = SapientMessage()
    try:
        message.ParseFromString(payload)
    except DecodeError as exc:
        raise CodecError("Invalid SapientMessage protobuf payload") from exc
    if validate:
        validate_message(message)
    return message
