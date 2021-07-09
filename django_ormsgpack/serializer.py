import pytz
from uuid import UUID
from typing import Any
from decimal import Decimal
from datetime import datetime
from .registry import class_fqname, SERIALIZER_ID
from .model import SerializableModel
import ormsgpack

TZ = "T_Z_"
MODEL = "S_M_"
UUID = "uUiD"

TZ_IDX = {tz: idx for idx, tz in enumerate(sorted(pytz.common_timezones))}
TZ_VAL = {idx: pytz.timezone(tz) for tz, idx in TZ_IDX.items()}


def _tz_id(tz: str) -> int:
    return pytz.all_timezones.index(tz)


def ormsgpack_serialize_defaults(val: Any):
    if isinstance(val, datetime):
        # "Pack Time with zone into 17 bytes."
        return (TZ, TZ_IDX[val.tzinfo.zone], val.timestamp())

    if isinstance(val, Decimal):
        return str(val)

    if isinstance(val, SerializableModel):
        classid = (
            getattr(val, SERIALIZER_ID)
            if hasattr(val, SERIALIZER_ID)
            else class_fqname(type(val))
        )
        return (MODEL, classid, val.to_tuple())


def serialize(val: Any):
    return ormsgpack.packb(
        val,
        default=ormsgpack_serialize_defaults,
        option=ormsgpack.OPT_PASSTHROUGH_DATETIME,
    )
