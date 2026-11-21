"""Shared identifiers and valid messages for the role-oriented examples."""

from sapient.messages import DetectionReport, Registration, StatusReport, Task, new_ulid

HOST = "127.0.0.1"
PORT = 5020

C2_ID = "c86a7289-1de9-493a-b17d-0c9f9f9838f4"
SENSOR_ID = "5ea410b7-9656-4d22-929d-3bad7bf15a21"
EFFECTOR_ID = "850fcc6a-c35f-4244-893f-bd209c459d21"


def registration(name: str, node_type: int, capability: str) -> Registration:
    """Return a small but valid registration for a demonstration node."""
    value = Registration(icd_version="BSI_Flex_335_v2.0", name=name)
    value.node_definition.add(node_type=node_type)
    value.capabilities.add(category="demo", type=capability)
    value.status_definition.status_interval.units = Registration.TIME_UNITS_SECONDS
    value.status_definition.status_interval.value = 10

    mode = value.mode_definition.add(
        mode_name="default",
        mode_type=Registration.MODE_TYPE_DEFAULT,
    )
    mode.settle_time.units = Registration.TIME_UNITS_SECONDS
    mode.settle_time.value = 0
    mode.task.region_definition.region_type.append(
        Registration.REGION_TYPE_AREA_OF_INTEREST
    )
    location_type = mode.task.region_definition.region_area.add()
    location_type.location_units = 1  # latitude/longitude degrees
    location_type.location_datum = 1  # WGS 84
    value.config_data.add(manufacturer="Example", model=name)
    return value


def status() -> StatusReport:
    return StatusReport(
        report_id=new_ulid(),
        system=StatusReport.SYSTEM_OK,
        info=StatusReport.INFO_NEW,
        mode="default",
    )


def detection(object_id: str, longitude: float, latitude: float) -> DetectionReport:
    """Create one WGS 84 observation of the same source-local object track."""
    value = DetectionReport(
        report_id=new_ulid(),
        object_id=object_id,
        detection_confidence=0.92,
    )
    value.location.x = longitude
    value.location.y = latitude
    value.location.coordinate_system = 1
    value.location.datum = 1
    value.classification.add(type="demo:vehicle", confidence=0.85)
    value.behaviour.add(type="moving", confidence=0.8)
    return value


def inspect_task() -> Task:
    value = Task(
        task_id=new_ulid(),
        task_name="Inspect sensor track",
        task_description="Demonstration command sent from C2 to the effector",
        control=Task.CONTROL_START,
    )
    value.command.request = "inspect latest sensor track"
    return value
