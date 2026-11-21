"""Dependency-free generation of SAPIENT identifiers."""

import secrets
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_ulid(*, timestamp_ms: int | None = None) -> str:
    """Return a canonical 26-character ULID."""
    instant = int(time.time_ns() // 1_000_000 if timestamp_ms is None else timestamp_ms)
    if not 0 <= instant < 2**48:
        raise ValueError("ULID timestamp must fit in 48 bits")
    value = (instant << 80) | secrets.randbits(80)
    characters = ["0"] * 26
    for index in range(25, -1, -1):
        characters[index] = _CROCKFORD[value & 31]
        value >>= 5
    return "".join(characters)


__all__ = ["new_ulid"]
