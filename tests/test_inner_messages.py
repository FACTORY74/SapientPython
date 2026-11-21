from sapient.messages import (
    AssociatedDetection,
    AssociatedFile,
    DetectionReport,
    ENUVelocity,
    FollowObject,
    Location,
    RangeBearing,
    Registration,
    Task,
)
from sapient.validation import validate_message
from tests.factories import NODE_ID, SECOND_ULID, ULID, detection, registration


def test_location_and_range_bearing_detection_alternatives() -> None:
    report = detection()
    validate_message(report)
    report.ClearField("location")
    report.range_bearing.CopyFrom(
        RangeBearing(
            azimuth=90,
            range=100,
            coordinate_system=1,
            datum=1,
        )
    )
    validate_message(report)


def test_velocity_classification_behaviour_and_associations() -> None:
    report = detection()
    report.enu_velocity.CopyFrom(ENUVelocity(east_rate=1, north_rate=2, up_rate=0))
    report.associated_file.add(type="image/jpeg", url="https://example.invalid/image.jpg")
    report.associated_detection.add(
        node_id=NODE_ID,
        object_id=SECOND_ULID,
        association_type=1,
    )
    validate_message(report)
    assert report.classification[0].sub_class[0].level == 1
    assert report.behaviour[0].type == "moving"


def test_registration_modes_capabilities_and_nested_configuration() -> None:
    value = registration()
    component = value.config_data[0].sub_components.add(
        manufacturer="OpenAI", model="camera"
    )
    component.sub_components.add(manufacturer="OpenAI", model="lens")
    validate_message(value)
    assert value.mode_definition[0].task.region_definition.region_type


def test_task_regions_filters_and_mobile_commands() -> None:
    value = Task(task_id=ULID, control=Task.CONTROL_START)
    region = value.region.add(
        type=Task.REGION_TYPE_AREA_OF_INTEREST,
        region_id=SECOND_ULID,
        region_name="patrol area",
    )
    first = region.region_area.location_list.locations.add(
        x=-1,
        y=52,
        coordinate_system=1,
        datum=1,
    )
    region.region_area.location_list.locations.add(
        x=first.x + 0.1,
        y=first.y + 0.1,
        coordinate_system=1,
        datum=1,
    )
    class_filter = region.class_filter.add(type="sapient_core:vehicle")
    class_filter.parameter.name = "confidence"
    class_filter.parameter.operator = 2
    class_filter.parameter.value = 0.5
    value.command.move_to.locations.add(
        x=-1,
        y=52,
        coordinate_system=1,
        datum=1,
    )
    validate_message(value)


def test_common_public_exports_construct() -> None:
    assert AssociatedFile(type="text/plain", url="https://example.invalid").type
    assert AssociatedDetection(node_id=NODE_ID, object_id=ULID).node_id
    assert FollowObject(follow_object_id=ULID).follow_object_id
    assert Location(x=0, y=0, coordinate_system=1, datum=1).datum == 1
