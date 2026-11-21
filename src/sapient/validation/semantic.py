"""Semantic rules stated by BSI Flex 335 but not encoded as proto options."""

import math
from datetime import UTC

from google.protobuf.message import Message

from sapient.errors import ValidationError


def _error(path: str, detail: str) -> None:
    raise ValidationError(f"{path} {detail}")


def _bounded(value: float, path: str, minimum: float, maximum: float) -> None:
    if not math.isfinite(value) or not minimum <= value <= maximum:
        _error(path, f"must be between {minimum:g} and {maximum:g}")


def _has(message: Message, field: str) -> bool:
    descriptor = message.DESCRIPTOR.fields_by_name[field]
    if descriptor.is_repeated:
        return bool(getattr(message, field))
    if descriptor.has_presence:
        return message.HasField(field)
    return getattr(message, field) != descriptor.default_value


def _valid_timestamp(message: Message, path: str) -> None:
    try:
        message.ToDatetime(tzinfo=UTC)
    except (OverflowError, ValueError) as exc:
        raise ValidationError(f"{path} is not a valid protobuf timestamp") from exc


def _validate_location(message: Message, path: str) -> None:
    coordinate_system = message.coordinate_system
    if message.utm_zone and coordinate_system != 5:  # LOCATION_COORDINATE_SYSTEM_UTM_M
        _error(f"{path}.utm_zone", "is only valid for UTM coordinates")
    if coordinate_system == 1:  # latitude/longitude degrees
        _bounded(message.x, f"{path}.x", -180, 180)
        _bounded(message.y, f"{path}.y", -90, 90)
    elif coordinate_system == 2:  # latitude/longitude radians
        _bounded(message.x, f"{path}.x", -math.pi, math.pi)
        _bounded(message.y, f"{path}.y", -math.pi / 2, math.pi / 2)


def _validate_location_type(message: Message, path: str) -> None:
    coordinates = message.WhichOneof("coordinates_oneof")
    datum = message.WhichOneof("datum_oneof")
    if coordinates == "location_units" and datum != "location_datum":
        _error(path, "must pair Cartesian coordinates with a location datum")
    if coordinates == "range_bearing_units" and datum != "range_bearing_datum":
        _error(path, "must pair range-bearing coordinates with a range-bearing datum")
    if message.zone and not (
        coordinates == "location_units" and message.location_units == 5
    ):
        _error(f"{path}.zone", "is only valid for UTM coordinates")


def _validate_task(message: Message, path: str) -> None:
    if not message.region and not _has(message, "command"):
        _error(path, "must define at least one region or command")
    if _has(message, "task_start_time") and _has(message, "task_end_time"):
        if message.task_end_time.ToNanoseconds() < message.task_start_time.ToNanoseconds():
            _error(f"{path}.task_end_time", "must not be before task_start_time")


def _validate_ack_reason(message: Message, path: str) -> None:
    name = message.DESCRIPTOR.full_name
    if name.endswith(".RegistrationAck"):
        if not message.acceptance and not message.ack_response_reason:
            _error(f"{path}.ack_response_reason", "is required when registration is rejected")
    elif name.endswith(".TaskAck"):
        if message.task_status in (2, 4) and not message.reason:
            _error(f"{path}.reason", "is required when a task is rejected or failed")
    elif name.endswith(".AlertAck"):
        if message.alert_ack_status == 2 and not message.reason:
            _error(f"{path}.reason", "is required when an alert is rejected")


def validate_semantics(message: Message, *, path: str) -> None:
    """Validate semantic constraints for one already structurally valid message."""
    name = message.DESCRIPTOR.full_name

    if name == "google.protobuf.Timestamp":
        _valid_timestamp(message, path)
        return

    confidence_fields = {
        "sapient_msg.bsi_flex_335_v2_0.DetectionReport": ("detection_confidence",),
        "sapient_msg.bsi_flex_335_v2_0.DetectionReport.DetectionReportClassification": ("confidence",),
        "sapient_msg.bsi_flex_335_v2_0.DetectionReport.SubClass": ("confidence",),
        "sapient_msg.bsi_flex_335_v2_0.DetectionReport.Behaviour": ("confidence",),
        "sapient_msg.bsi_flex_335_v2_0.Alert": ("ranking", "confidence"),
    }
    for field in confidence_fields.get(name, ()):
        if _has(message, field):
            _bounded(getattr(message, field), f"{path}.{field}", 0, 1)

    if name == "sapient_msg.bsi_flex_335_v2_0.StatusReport.Power":
        if _has(message, "level") and not 0 <= message.level <= 100:
            _error(f"{path}.level", "must be between 0 and 100")
    elif name == "sapient_msg.bsi_flex_335_v2_0.Location":
        _validate_location(message, path)
    elif name == "sapient_msg.bsi_flex_335_v2_0.Registration.LocationType":
        _validate_location_type(message, path)
    elif name == "sapient_msg.bsi_flex_335_v2_0.Task":
        _validate_task(message, path)
    elif name in {
        "sapient_msg.bsi_flex_335_v2_0.RegistrationAck",
        "sapient_msg.bsi_flex_335_v2_0.TaskAck",
        "sapient_msg.bsi_flex_335_v2_0.AlertAck",
    }:
        _validate_ack_reason(message, path)
    elif name == "sapient_msg.bsi_flex_335_v2_0.DetectionReport.PredictedLocation":
        if message.WhichOneof("predicted_location_oneof") is None:
            _error(f"{path}.predicted_location_oneof", "must select one value")
    elif name in {
        "sapient_msg.bsi_flex_335_v2_0.DetectionReport.DetectionReportClassification",
        "sapient_msg.bsi_flex_335_v2_0.DetectionReport.SubClass",
    }:
        if ":" not in message.type or message.type.startswith(":") or message.type.endswith(":"):
            _error(f"{path}.type", "must use the <namespace>:<value> format")
        if name.endswith(".SubClass") and message.level < 0:
            _error(f"{path}.level", "must not be negative")
    elif name == "sapient_msg.bsi_flex_335_v2_0.SapientMessage":
        if message.WhichOneof("content") == "detection_report":
            prediction = message.detection_report.prediction_location
            if _has(message.detection_report, "prediction_location") and _has(
                prediction, "predicted_timestamp"
            ):
                if prediction.predicted_timestamp.ToNanoseconds() <= message.timestamp.ToNanoseconds():
                    _error(
                        f"{path}.detection_report.prediction_location.predicted_timestamp",
                        "must be later than the detection timestamp",
                    )
