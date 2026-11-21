import pytest

from sapient.codec import decode_message, encode_message
from sapient.errors import ValidationError
from sapient.messages import (
    Alert,
    AlertAck,
    DetectionReport,
    Error,
    Registration,
    RegistrationAck,
    StatusReport,
    Task,
    TaskAck,
    create_message,
)
from sapient.validation import validate_message
from tests.factories import FUSION_ID, NODE_ID, ULID, outer_messages


@pytest.mark.parametrize("payload", outer_messages(), ids=lambda value: value.DESCRIPTOR.name)
def test_every_outer_message_round_trips(payload) -> None:
    envelope = create_message(
        sender_id=NODE_ID,
        destination_id=FUSION_ID,
        content=payload,
    )
    assert decode_message(encode_message(envelope)) == envelope


@pytest.mark.parametrize(
    "payload",
    [
        Registration(),
        RegistrationAck(),
        StatusReport(),
        DetectionReport(),
        Task(),
        TaskAck(),
        Alert(),
        AlertAck(),
        Error(),
    ],
    ids=lambda value: value.DESCRIPTOR.name,
)
def test_every_outer_message_has_a_negative_validation_case(payload) -> None:
    with pytest.raises(ValidationError):
        validate_message(payload)


def test_envelope_rejects_unsupported_inner_message() -> None:
    with pytest.raises(TypeError, match="Unsupported"):
        create_message(
            sender_id=NODE_ID,
            content=StatusReport.Power(level=50),
        )
