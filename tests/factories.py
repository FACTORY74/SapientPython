"""Valid representative BSI Flex 335 messages used across tests."""

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
)

NODE_ID = "5ea410b7-9656-4d22-929d-3bad7bf15a21"
FUSION_ID = "c86a7289-1de9-493a-b17d-0c9f9f9838f4"
ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
SECOND_ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAW"


def registration() -> Registration:
    value = Registration(icd_version="BSI_Flex_335_v2.0", name="Test edge node")
    value.node_definition.add(node_type=Registration.NODE_TYPE_OTHER)
    value.capabilities.add(category="sensor", type="detection")
    value.status_definition.status_interval.units = Registration.TIME_UNITS_SECONDS
    value.status_definition.status_interval.value = 10
    mode = value.mode_definition.add(
        mode_name="default",
        mode_type=Registration.MODE_TYPE_DEFAULT,
    )
    mode.settle_time.units = Registration.TIME_UNITS_SECONDS
    mode.settle_time.value = 0
    region = mode.task.region_definition
    region.region_type.append(Registration.REGION_TYPE_AREA_OF_INTEREST)
    location_type = region.region_area.add()
    location_type.location_units = 1
    location_type.location_datum = 1
    value.config_data.add(manufacturer="OpenAI", model="SAPIENT test node")
    return value


def status(*, system: int = StatusReport.SYSTEM_OK) -> StatusReport:
    return StatusReport(
        report_id=ULID,
        system=system,
        info=StatusReport.INFO_NEW,
        mode="default",
    )


def detection() -> DetectionReport:
    value = DetectionReport(report_id=ULID, object_id=SECOND_ULID, detection_confidence=0.9)
    value.location.x = -1.5
    value.location.y = 52.0
    value.location.coordinate_system = 1
    value.location.datum = 1
    classification = value.classification.add(type="sapient_core:vehicle", confidence=0.8)
    classification.sub_class.add(type="sapient_core:car", confidence=0.7, level=1)
    value.behaviour.add(type="moving", confidence=0.6)
    return value


def task() -> Task:
    value = Task(task_id=ULID, control=Task.CONTROL_START)
    value.command.request = "snapshot"
    return value


def outer_messages():
    return [
        registration(),
        RegistrationAck(acceptance=True),
        status(),
        detection(),
        task(),
        TaskAck(task_id=ULID, task_status=TaskAck.TASK_STATUS_ACCEPTED),
        Alert(alert_id=ULID, alert_type=Alert.ALERT_TYPE_INFORMATION),
        AlertAck(alert_id=ULID, alert_ack_status=AlertAck.ALERT_ACK_STATUS_ACCEPTED),
        Error(packet=b"bad packet", error_message=["invalid"]),
    ]
