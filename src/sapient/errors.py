"""Exception hierarchy for the public SAPIENT API."""


class SapientError(Exception):
    """Base class for SAPIENT interface errors."""


class ValidationError(SapientError, ValueError):
    """A message does not satisfy the SAPIENT schema constraints."""


class CodecError(SapientError, ValueError):
    """A message cannot be serialized or deserialized."""


class FramingError(SapientError, ValueError):
    """A byte stream contains an invalid SAPIENT frame."""


class ConnectionClosedError(SapientError, EOFError):
    """The transport closed before a complete message was received."""


class EndOfStream(SapientError, EOFError):
    """The peer closed cleanly between SAPIENT frames."""


class ProtocolStateError(SapientError, RuntimeError):
    """An operation or message is invalid in the current protocol state."""


class RegistrationRejectedError(ProtocolStateError):
    """A fusion node rejected an edge-node registration."""


class UnexpectedAcknowledgementError(ProtocolStateError):
    """An acknowledgement does not match a tracked task or alert."""


class UnknownDestinationError(ProtocolStateError):
    """A transparent message handler cannot resolve a destination node."""
