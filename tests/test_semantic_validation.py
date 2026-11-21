from datetime import UTC, datetime, timedelta

import pytest
from google.protobuf.timestamp_pb2 import Timestamp

from sapient.errors import ValidationError
from sapient.messages import Alert, AlertAck, DetectionReport, RegistrationAck, StatusReport, Task, TaskAck, create_message
from sapient.messages.geometry import Location
from sapient.validation import validate_message
from sapient_msg.bsi_flex_335_v2_0.registration_pb2 import Registration

ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
UUID = "5ea410b7-9656-4d22-929d-3bad7bf15a21"


@pytest.mark.parametrize("value", [-0.01, 1.01, float("nan"), float("inf")])
def test_detection_confidence_is_bounded(value: float) -> None:
    report = DetectionReport(report_id=ULID, object_id=ULID, detection_confidence=value)
    report.location.x = 0
    report.location.y = 0
    report.location.coordinate_system = 1
    report.location.datum = 1
    with pytest.raises(ValidationError, match="between 0 and 1"):
        validate_message(report)


@pytest.mark.parametrize("field", ["ranking", "confidence"])
def test_alert_probabilities_are_bounded(field: str) -> None:
    alert = Alert(alert_id=ULID)
    setattr(alert, field, 1.1)
    with pytest.raises(ValidationError, match="between 0 and 1"):
        validate_message(alert)


def test_nested_classification_confidence_and_namespace() -> None:
    classification = DetectionReport.DetectionReportClassification(type="vehicle", confidence=0.5)
    with pytest.raises(ValidationError, match="namespace"):
        validate_message(classification)
    classification.type = "sapient_core:vehicle"
    classification.confidence = -0.1
    with pytest.raises(ValidationError, match="between 0 and 1"):
        validate_message(classification)


def test_battery_percentage_is_bounded() -> None:
    power = StatusReport.Power(level=101)
    with pytest.raises(ValidationError, match="between 0 and 100"):
        validate_message(power)


def test_task_requires_region_or_command() -> None:
    task = Task(task_id=ULID, control=Task.CONTROL_START)
    with pytest.raises(ValidationError, match="region or command"):
        validate_message(task)
    task.command.request = "snapshot"
    validate_message(task)


def test_task_end_cannot_precede_start() -> None:
    start = Timestamp()
    start.FromDatetime(datetime(2026, 1, 2, tzinfo=UTC))
    end = Timestamp()
    end.FromDatetime(datetime(2026, 1, 1, tzinfo=UTC))
    task = Task(task_id=ULID, control=Task.CONTROL_START, task_start_time=start, task_end_time=end)
    task.command.request = "snapshot"
    with pytest.raises(ValidationError, match="must not be before"):
        validate_message(task)


def test_invalid_timestamp_is_rejected() -> None:
    timestamp = Timestamp(seconds=253402300800)
    with pytest.raises(ValidationError, match="valid protobuf timestamp"):
        validate_message(timestamp)


def test_location_bounds_and_utm_zone_consistency() -> None:
    location = Location(x=181, y=0, coordinate_system=1, datum=1)
    with pytest.raises(ValidationError, match="between -180 and 180"):
        validate_message(location)
    location.x = 1
    location.utm_zone = "30U"
    with pytest.raises(ValidationError, match="only valid for UTM"):
        validate_message(location)


def test_registration_location_type_pairs_coordinate_and_datum() -> None:
    location_type = Registration.LocationType(location_units=1, range_bearing_datum=1)
    with pytest.raises(ValidationError, match="pair Cartesian"):
        validate_message(location_type)


@pytest.mark.parametrize(
    "ack",
    [
        RegistrationAck(acceptance=False),
        TaskAck(task_id=ULID, task_status=TaskAck.TASK_STATUS_REJECTED),
        TaskAck(task_id=ULID, task_status=TaskAck.TASK_STATUS_FAILED),
        AlertAck(alert_id=ULID, alert_ack_status=AlertAck.ALERT_ACK_STATUS_REJECTED),
    ],
)
def test_negative_acknowledgements_require_reason(ack) -> None:
    with pytest.raises(ValidationError, match="reason"):
        validate_message(ack)


def test_prediction_requires_location_and_later_timestamp() -> None:
    prediction = DetectionReport.PredictedLocation()
    with pytest.raises(ValidationError, match="must select"):
        validate_message(prediction)

    report = DetectionReport(report_id=ULID, object_id=ULID)
    report.location.x = 0
    report.location.y = 0
    report.location.coordinate_system = 1
    report.location.datum = 1
    report.prediction_location.location.CopyFrom(report.location)
    instant = datetime.now(UTC)
    report.prediction_location.predicted_timestamp.FromDatetime(instant - timedelta(seconds=1))
    envelope = create_message(sender_id=UUID, content=report, timestamp=instant)
    with pytest.raises(ValidationError, match="later than"):
        validate_message(envelope)


def test_valid_semantic_values_pass() -> None:
    alert = Alert(alert_id=ULID, ranking=0, confidence=1)
    validate_message(alert)
