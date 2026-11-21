"""Construct, validate, and round-trip every principal outer message type."""

from sapient.codec import decode_message, encode_message
from sapient.messages import (
    Alert,
    AlertAck,
    DetectionReport,
    Error,
    RegistrationAck,
    TaskAck,
    create_message,
)

from _fixtures import NODE_ID, outer_messages


def main() -> None:
    for payload in outer_messages():
        envelope = create_message(sender_id=NODE_ID, content=payload)
        restored = decode_message(encode_message(envelope))
        print(f"{payload.DESCRIPTOR.name}: {len(encode_message(restored))} bytes")


if __name__ == "__main__":
    main()
