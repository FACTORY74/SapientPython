import importlib
import pkgutil

import pytest
from google.protobuf import message_factory
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message

from sapient.errors import ValidationError
from sapient.messages import StatusReport, create_message
from sapient.validation import validate_message
from sapient_msg import proto_options_pb2
import sapient_msg.bsi_flex_335_v2_0 as schema_package


UUID_VALUE = "5ea410b7-9656-4d22-929d-3bad7bf15a21"
ULID_VALUE = "01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _field_options(field: FieldDescriptor):
    options = field.GetOptions()
    if options.HasExtension(proto_options_pb2.field_options):
        return options.Extensions[proto_options_pb2.field_options]
    return None


def _set_valid_value(message: Message, field: FieldDescriptor) -> None:
    options = _field_options(field)
    if field.type == FieldDescriptor.TYPE_MESSAGE:
        target = getattr(message, field.name)
        if field.is_repeated:
            target = target.add()
        _populate_mandatory(target)
        return

    if options is not None and options.is_uuid:
        value = UUID_VALUE
    elif options is not None and options.is_ulid:
        value = ULID_VALUE
    elif field.type == FieldDescriptor.TYPE_ENUM:
        value = next(item.number for item in field.enum_type.values if item.number > 0)
    elif field.type == FieldDescriptor.TYPE_STRING:
        value = "value"
    elif field.type == FieldDescriptor.TYPE_BYTES:
        value = b"value"
    elif field.type == FieldDescriptor.TYPE_BOOL:
        value = True
    else:
        value = 1

    target = getattr(message, field.name) if field.is_repeated else None
    if field.is_repeated:
        target.append(value)
    else:
        setattr(message, field.name, value)


def _populate_mandatory(message: Message) -> None:
    selected_oneofs: set[str] = set()
    for field in message.DESCRIPTOR.fields:
        options = _field_options(field)
        mandatory = options is not None and options.is_mandatory
        if field.containing_oneof is not None:
            oneof = field.containing_oneof
            oneof_options = oneof.GetOptions()
            oneof_mandatory = (
                oneof_options.HasExtension(proto_options_pb2.oneof_options)
                and oneof_options.Extensions[proto_options_pb2.oneof_options].is_mandatory
            )
            if oneof_mandatory:
                mandatory = oneof.name not in selected_oneofs
                if mandatory:
                    selected_oneofs.add(oneof.name)
        if mandatory:
            _set_valid_value(message, field)


def _mandatory_enum_fields():
    modules = []
    for module_info in pkgutil.iter_modules(schema_package.__path__):
        if module_info.name.endswith("_pb2"):
            modules.append(
                importlib.import_module(f"{schema_package.__name__}.{module_info.name}")
            )

    fields = []
    visited = set()

    def visit(descriptor) -> None:
        if descriptor.full_name in visited:
            return
        visited.add(descriptor.full_name)
        for field in descriptor.fields:
            options = _field_options(field)
            if (
                options is not None
                and options.is_mandatory
                and field.type == FieldDescriptor.TYPE_ENUM
            ):
                fields.append((descriptor, field))
        for nested in descriptor.nested_types:
            visit(nested)

    for module in modules:
        for descriptor in module.DESCRIPTOR.message_types_by_name.values():
            visit(descriptor)
    return fields


def test_missing_mandatory_status_field_is_rejected() -> None:
    status = StatusReport(
        report_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        system=StatusReport.SYSTEM_OK,
        info=StatusReport.INFO_NEW,
    )
    message = create_message(
        sender_id="5ea410b7-9656-4d22-929d-3bad7bf15a21",
        content=status,
    )
    with pytest.raises(ValidationError, match="mode is mandatory"):
        validate_message(message)


def test_invalid_sender_uuid_is_rejected() -> None:
    status = StatusReport(
        report_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        system=StatusReport.SYSTEM_OK,
        info=StatusReport.INFO_NEW,
        mode="default",
    )
    message = create_message(sender_id="not-a-uuid", content=status)
    with pytest.raises(ValidationError, match="must be a UUID"):
        validate_message(message)


def test_sender_uuid_must_be_version_four() -> None:
    message = create_message(
        sender_id="6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        content=StatusReport(
            report_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            system=StatusReport.SYSTEM_OK,
            info=StatusReport.INFO_NEW,
            mode="default",
        ),
    )
    with pytest.raises(ValidationError, match="UUID version 4"):
        validate_message(message)


@pytest.mark.parametrize(
    ("descriptor", "enum_field"),
    _mandatory_enum_fields(),
    ids=lambda value: getattr(value, "full_name", getattr(value, "name", str(value))),
)
def test_every_mandatory_enum_rejects_unspecified(descriptor, enum_field) -> None:
    message_class = message_factory.GetMessageClass(descriptor)
    message = message_class()
    _populate_mandatory(message)
    if enum_field.is_repeated:
        values = getattr(message, enum_field.name)
        del values[:]
        values.append(0)
    else:
        setattr(message, enum_field.name, 0)

    with pytest.raises(
        ValidationError,
        match=rf"{enum_field.name} must not use the UNSPECIFIED enum value",
    ):
        validate_message(message)


def test_mandatory_nonzero_enums_are_accepted() -> None:
    status = StatusReport(
        report_id=ULID_VALUE,
        system=StatusReport.SYSTEM_OK,
        info=StatusReport.INFO_NEW,
        mode="default",
    )
    validate_message(status)
