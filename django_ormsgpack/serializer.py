import pytz
from uuid import UUID
from typing import Any
from decimal import Decimal
from datetime import datetime
from .registry import class_fqname, SERIALIZER_ID
from .model import SerializableModel
from .serializer_fns import serialize_dt, deserialize_dt
import ormsgpack

TZ = "T_Z_"
MODEL = "S_M_"
UUID_IDENTIFIER = "uUiD"


def _tz_id(tz: str) -> int:
    return pytz.all_timezones.index(tz)


# pylint: disable=protected-access
def ormsgpack_serialize_defaults(val: Any):
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


def deserialize(val: Any):
    if isinstance(
        val,
        (
            list,
            tuple,
        ),
    ):
        if val[0] == UUID_IDENTIFIER:
            return UUID(bytes=val[1])
        if val[0] == TZ:
            return deserialize_dt(val[1], val[2])
        return [deserialize(subval) for subval in val]
    return val


def serialize(val: Any):
    return ormsgpack.packb(
        val,
        default=ormsgpack_serialize_defaults,
        option=ormsgpack.OPT_PASSTHROUGH_DATETIME,
    )
