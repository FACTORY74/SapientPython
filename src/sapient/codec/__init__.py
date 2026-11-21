"""Serialization and BSI stream framing."""

from sapient.codec.framing import FrameDecoder, frame_payload
from sapient.codec.protobuf import decode_message, encode_message

__all__ = ["FrameDecoder", "decode_message", "encode_message", "frame_payload"]
