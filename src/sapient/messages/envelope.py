"""Creation of the common SAPIENT message envelope."""

from datetime import UTC, datetime
from typing import Final

from google.protobuf.message import Message
from google.protobuf.timestamp_pb2 import Timestamp
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage

_CONTENT_FIELDS: Final[dict[str, str]] = {
    "Registration": "registration",
    "RegistrationAck": "registration_ack",
    "StatusReport": "status_report",
    "DetectionReport": "detection_report",
    "Task": "task",
    "TaskAck": "task_ack",
    "Alert": "alert",
    "AlertAck": "alert_ack",
    "Error": "error",
}


def create_message(
    *,
    sender_id: str,
    content: Message,
    destination_id: str | None = None,
    timestamp: datetime | None = None,
    additional_information: str | None = None,
) -> SapientMessage:
    """Create an envelope and copy a supported outer payload into it."""
    content_field = _CONTENT_FIELDS.get(content.DESCRIPTOR.name)
    if content_field is None:
        raise TypeError(f"Unsupported SAPIENT outer message: {content.DESCRIPTOR.full_name}")

    instant = timestamp or datetime.now(UTC)
    if instant.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")

    protobuf_time = Timestamp()
    protobuf_time.FromDatetime(instant.astimezone(UTC))
    envelope = SapientMessage(timestamp=protobuf_time, node_id=sender_id)
    if destination_id is not None:
        envelope.destination_id = destination_id
    if additional_information is not None:
        envelope.additional_information = additional_information
    getattr(envelope, content_field).CopyFrom(content)
    return envelope
