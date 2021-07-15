from __future__ import annotations
import pytz
from uuid import UUID
import logging
from typing import Iterable, Union, Any, Type, List
from datetime import datetime
from django.db.models import fields, Model
from django.db.models.fields import Field, UUIDField
from .serializable import Serializable
from .code import Code


TZ = "T_Z_"
MODEL = "S_M_"
UUID_IDENTIFIER = "uUiD"

FROM_TUPLE_TEMPLATE = """
def __from_tuple(cls, val: List[Any]):
    instance = cls()
    fields = cls.get_serializer_fields()
{expressions}
    return instance

TheModel.register_deserializer(classmethod(__from_tuple))
"""

TZ_IDX = {tz: idx for idx, tz in enumerate(sorted(pytz.common_timezones))}
TZ_VAL = {idx: pytz.timezone(tz) for tz, idx in TZ_IDX.items()}

logger = logging.getLogger(__name__)


def _build_deserialization_expression(idx: int, field: Field, depth=0) -> str:
    code = Code()
    logger.debug("SPOOPY")
    if field.is_relation:
        pk_field: Field = field.related_model._meta.pk
        code.add(f"if val[{idx}]:")
        if isinstance(pk_field, UUIDField):
            code.add(f"if val[{idx}][0] == '{UUID_IDENTIFIER}':")
            code.add(f"instance.{field.name}_id = UUID(bytes=val[{idx}][1])")
            code.add_globals(UUID)
        else:
            code.add(f"if not isinstance(val[{idx}], (list, tuple)):")
            code.add(f"instance.{field.name}_id = fields[{idx}].to_python(val[{idx}])")
        code.end_block()
        code.add("else:")
        code.add(
            f"instance.{field.name} = fields[{idx}].related_model.from_tuple(val[{idx}])"
        )
    else:
        if isinstance(field, UUIDField):
            code.add_globals(UUID)
            code.add(
                f"instance.{field.name} = UUID(bytes=val[{idx}][1]) if isinstance(val[{idx}], tuple) else fields[{idx}].to_python(val[{idx}])"
            )
        else:
            code.add(f"instance.{field.name} = fields[{idx}].to_python(val[{idx}])")
    return code


def compile_from_tuple_function(ModelClass: Type[Model], deserializers_dict: dict):
    fields: List[Field] = ModelClass._meta.fields
    code = Code()
    code.add_globals(ModelClass=ModelClass)
    code.add("def from_tuple(val):")
    code.add("instance = ModelClass()")
    code.add("fields = ModelClass.get_serializer_fields()")
    code.add(
        *(
            _build_deserialization_expression(idx, field)
            for idx, field in enumerate(fields)
        )
    )
    code.add("return instance")
    code.full_outdent()
    code.add("_DESERIALIZERS[ModelClass] = from_tuple")
    code.add_globals(_DESERIALIZERS=deserializers_dict)
    code.exec()
    return code


def serialize_dt(dt: datetime):
    return (TZ, TZ_IDX[dt.tzinfo.zone], dt.timestamp())


def deserialize_dt(zone_id: int, timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp, TZ_VAL[zone_id])


def deserialize_model(_, class_id: Union[int, str], val: Iterable[Any]):
    ...


DESERIALIZE_INT_FK_TEMPLATE = """if {val_name}[{idx}]:
    if isinstance({val_name}[{idx}], int):
        {obj_name}.{field.name}_id = UUID(bytes={val_name}[{idx}][1])
    else:
        {obj_name}.{field.name} = deserialize_model(*{val_name}[{idx}])"""


def deserialize_uuid_fk_expr(
    obj_name: str, val_name: str, idx: int, field: fields.Field
) -> Iterable[str]:
    block = DESERIALIZE_UUID_FK_TEMPLATE.format(**locals())
    return [line for line in block.split("\n") if line.strip()]


DESERIALIZE_UUID_FK_TEMPLATE = """if {val_name}[{idx}]:
    if {val_name}[{idx}][0] == '{UUID_IDENTIFIER}':
        {obj_name}.{field.name}_id = UUID(bytes={val_name}[{idx}][1])
    else:
        {obj_name}.{field.name} = deserialize_model(*{val_name}[{idx}])"""


def deserialize_uuid_fk_expr(
    obj_name: str, val_name: str, idx: int, field: fields.Field
) -> Iterable[str]:
    block = DESERIALIZE_UUID_FK_TEMPLATE.format(**locals())
    return [line for line in block.split("\n") if line.strip()]


def wrap_expr(expr: str, field: fields.Field) -> str:
    if isinstance(field, fields.DateTimeField):
        return f"serialize_dt({expr})"
    if isinstance(field, fields.UUIDField):
        return f"('{UUID_IDENTIFIER}', ({expr}).bytes)"
    if isinstance(field, fields.DecimalField):
        return f"str({expr})"
    if field.is_relation:
        if hasattr(field.related_model, "to_tuple"):
            return f"({expr}).to_tuple()"
        return expr + "_id"
    return expr
