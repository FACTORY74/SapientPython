"""Small valid messages shared by the executable examples."""

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


def registration() -> Registration:
    value = Registration(icd_version="BSI_Flex_335_v2.0", name="Example edge node")
    value.node_definition.add(node_type=Registration.NODE_TYPE_OTHER)
    value.capabilities.add(category="sensor", type="detection")
    value.status_definition.status_interval.units = Registration.TIME_UNITS_SECONDS
    value.status_definition.status_interval.value = 10
    mode = value.mode_definition.add(
        mode_name="default", mode_type=Registration.MODE_TYPE_DEFAULT
    )
    mode.settle_time.units = Registration.TIME_UNITS_SECONDS
    mode.settle_time.value = 0
    region = mode.task.region_definition
    region.region_type.append(Registration.REGION_TYPE_AREA_OF_INTEREST)
    location = region.region_area.add()
    location.location_units = 1
    location.location_datum = 1
    value.config_data.add(manufacturer="Example", model="Node")
    return value


def status() -> StatusReport:
    return StatusReport(
        report_id=ULID,
        system=StatusReport.SYSTEM_OK,
        info=StatusReport.INFO_NEW,
        mode="default",
    )


def outer_messages():
    detection = DetectionReport(report_id=ULID, object_id=ULID)
    detection.location.x = 0
    detection.location.y = 0
    detection.location.coordinate_system = 1
    detection.location.datum = 1
    task = Task(task_id=ULID, control=Task.CONTROL_START)
    task.command.request = "snapshot"
    return [
        registration(),
        RegistrationAck(acceptance=True),
        status(),
        detection,
        task,
        TaskAck(task_id=ULID, task_status=TaskAck.TASK_STATUS_ACCEPTED),
        Alert(alert_id=ULID),
        AlertAck(alert_id=ULID, alert_ack_status=AlertAck.ALERT_ACK_STATUS_ACCEPTED),
        Error(packet=b"bad", error_message=["example"]),
    ]
