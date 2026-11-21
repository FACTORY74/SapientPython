"""Validation using the custom options supplied with the SAPIENT schemas."""

import re
from uuid import UUID

from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message
from sapient_msg import proto_options_pb2

from sapient.errors import ValidationError
from sapient.validation.semantic import validate_semantics

_ULID = re.compile(r"[0-7][0-9A-HJKMNP-TV-Z]{25}\Z")


def _present(message: Message, field: FieldDescriptor) -> bool:
    if field.is_repeated:
        return bool(getattr(message, field.name))
    if field.has_presence:
        return message.HasField(field.name)
    value = getattr(message, field.name)
    return value != field.default_value


def _options(field: FieldDescriptor):
    options = field.GetOptions()
    if options.HasExtension(proto_options_pb2.field_options):
        return options.Extensions[proto_options_pb2.field_options]
    return None


def _validate_identifier(value: str, *, kind: str, path: str) -> None:
    if kind == "uuid":
        try:
            identifier = UUID(value)
        except (ValueError, AttributeError) as exc:
            raise ValidationError(f"{path} must be a UUID version 4") from exc
        if identifier.version != 4:
            raise ValidationError(f"{path} must be a UUID version 4")
    elif not _ULID.fullmatch(value):
        raise ValidationError(f"{path} must be a canonical uppercase ULID")


def validate_message(message: Message, *, path: str | None = None) -> None:
    """Validate a protobuf message against SAPIENT custom annotations."""
    current_path = path or message.DESCRIPTOR.name

    for oneof in message.DESCRIPTOR.oneofs:
        options = oneof.GetOptions()
        if (
            options.HasExtension(proto_options_pb2.oneof_options)
            and options.Extensions[proto_options_pb2.oneof_options].is_mandatory
            and message.WhichOneof(oneof.name) is None
        ):
            raise ValidationError(f"{current_path}.{oneof.name} must select one value")

    for field in message.DESCRIPTOR.fields:
        present = _present(message, field)
        options = _options(field)
        field_path = f"{current_path}.{field.name}"
        if options is not None and options.is_mandatory and not present:
            raise ValidationError(f"{field_path} is mandatory")
        if not present:
            continue

        value = getattr(message, field.name)
        values = value if field.is_repeated else (value,)
        for item in values:
            if (
                options is not None
                and options.is_mandatory
                and field.type == FieldDescriptor.TYPE_ENUM
                and item == 0
            ):
                raise ValidationError(
                    f"{field_path} must not use the UNSPECIFIED enum value"
                )
            if options is not None and options.is_uuid:
                _validate_identifier(item, kind="uuid", path=field_path)
            if options is not None and options.is_ulid:
                _validate_identifier(item, kind="ulid", path=field_path)
            if field.type == FieldDescriptor.TYPE_MESSAGE:
                validate_message(item, path=field_path)

    validate_semantics(message, path=current_path)
