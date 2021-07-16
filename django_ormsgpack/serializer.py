from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import ormsgpack
import pytz

from .model import SerializableModel
from .registry import SERIALIZER_ID, class_fqname
from .serializer_fns import (
    deserialize_dt,
    serialize_dt,
    deserialize_model,
    TZ,
    MODEL,
    UUID_IDENTIFIER,
)


def _tz_id(tz: str) -> int:
    return pytz.all_timezones.index(tz)


# pylint: disable=protected-access
def ormsgpack_serialize_defaults(val: Any) -> Any:
    if isinstance(val, datetime):
        # "Pack Time with zone into 17 bytes."
        return serialize_dt(val)

    if isinstance(val, UUID):
        return (UUID_IDENTIFIER, val.bytes)

    if isinstance(val, Decimal):
        return str(val)

    if isinstance(val, SerializableModel):
        klass = val.__class__
        classid = (
            class_fqname(klass)
            if klass._serializer_id is None
            else klass._serializer_id
        )
        return (MODEL, classid, val.to_tuple())


def deserialize(val: bytes) -> Any:
    """
    Unpack and unwrap the given value.

    :param val: Should be a value returned by the `serialize` function.
    """
    return _unwrap(ormsgpack.unpackb(val))


def _unwrap(unpacked: Any) -> Any:
    if isinstance(
        unpacked,
        (
            list,
            tuple,
        ),
    ):
        if unpacked[0] == UUID_IDENTIFIER:
            return UUID(bytes=unpacked[1])
        if unpacked[0] == TZ:
            return deserialize_dt(unpacked[1], unpacked[2])
        if unpacked[0] == MODEL:
            return deserialize_model(unpacked[1], unpacked[2])
        return [_unwrap(subval) for subval in unpacked]
    if isinstance(unpacked, dict):
        return {key: _unwrap(val) for key, val in unpacked.items()}
    return unpacked


def serialize(val: Any) -> str:
    return ormsgpack.packb(
        val,
        default=ormsgpack_serialize_defaults,
        option=ormsgpack.OPT_PASSTHROUGH_DATETIME,
    )
