from __future__ import annotations
import pytz
from uuid import UUID
import logging
from typing import Iterable, Union, Any, Type, List, Set
from datetime import datetime
from django.db.models import fields, Model
from django.db.models.fields import Field, UUIDField, DateTimeField, DecimalField
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
                f"instance.{field.name} = UUID(bytes=val[{idx}][1]) if isinstance(val[{idx}], (list, tuple)) else fields[{idx}].to_python(val[{idx}])"
            )
        elif isinstance(field, DateTimeField):
            code.add(f"instance.{field.name} = (")
            code.start_block()
            code.add("None")
            code.add(f"if val[{idx}] is None else")
            code.add(f"datetime.fromtimestamp(val[{idx}][2], TZ_VAL[val[{idx}][1]])")
            code.outdent()
            code.add(")")
            code.add_globals(datetime=datetime, TZ_VAL=TZ_VAL)
        else:
            code.add(f"instance.{field.name} = fields[{idx}].to_python(val[{idx}])")
    return code


def compile_to_tuple_function(ModelClass: Type[Model], serializers_dict: dict):
    metadata = ModelClass.Serialize  # pylint: disable=E1101
    load_related: bool = getattr(metadata, "load_related", False)

    serializer_fields: List[Field] = ModelClass.get_serializer_fields()
    pk_only: Set[str] = getattr(metadata, "pk_only", set())
    # if not field.is_relation or field.name not in pk_only and load_related:

    code = Code()
    fn_name = f"_{ModelClass.__name__}_to_tuple"
    code.add_globals(ModelClass=ModelClass)
    code.add(f"def {fn_name}(val):")
    code.add("return (")
    code.start_block()
    for field in serializer_fields:

        def null_check(expr: str) -> str:
            return f"None if val.{field.name} is None else {expr}"

        if isinstance(field, UUIDField):
            code.add(null_check(f"('{UUID_IDENTIFIER}', val.{field.name}.bytes)") + ",")
        elif isinstance(field, DecimalField):
            code.add(null_check(f"str(val.{field.name})") + ",")
        elif isinstance(field, DateTimeField):
            code.add(
                null_check(
                    f"('{TZ}', TZ_IDX[val.{field.name}.tzinfo.zone], val.{field.name}.timestamp())"
                    + ","
                )
            )
            code.add_globals(TZ_IDX=TZ_IDX)
        elif field.is_relation:
            # Determine if should be serialized or just use id.
            related_class = field.related_model
            if isinstance(related_class._meta.pk, UUIDField):
                id_expr = f"(None if val.{field.name}_id is None else ('{UUID_IDENTIFIER}', val.{field.name}_id.bytes))"
            else:
                id_expr = f"val.{field.name}_id"

            if field.name in pk_only or not hasattr(related_class, "to_tuple"):
                code.add(id_expr + ",")
                continue

            # By now we know that we can and should serialize the value
            # IF it is there in the cached fields.
            code.add(
                f"val.{field.name} if '{field.name}' in val._state.fields_cache else {id_expr},"
            )
        else:
            code.add(f"val.{field.name},")

    code.outdent()
    code.add(")")
    code.full_outdent()

    code.add(f"_SERIALIZERS[ModelClass] = {fn_name}")
    code.add_globals(_SERIALIZERS=serializers_dict)
    code.exec(f"{fn_name}.py")
    return code


def compile_from_tuple_function(ModelClass: Type[Model], deserializers_dict: dict):
    fields: List[Field] = ModelClass.get_serializer_fields()
    code = Code()
    fn_name = f"_{ModelClass.__name__}_from_tuple"
    code.add_globals(ModelClass=ModelClass)
    code.add_globals(UUID)
    code.add(f"def {fn_name}(val):")
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
    code.add(f"_DESERIALIZERS[ModelClass] = {fn_name}")
    code.add_globals(_DESERIALIZERS=deserializers_dict)
    code.exec(f"{fn_name}.py")
    return code


def serialize_dt(dt: datetime):
    return (TZ, TZ_IDX[dt.tzinfo.zone], dt.timestamp())


def deserialize_dt(zone_id: int, timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp, TZ_VAL[zone_id])


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
