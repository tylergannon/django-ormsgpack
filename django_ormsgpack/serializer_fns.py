from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Iterable, List, Set, Type, Union
from uuid import UUID

import pytz
from django.db.models import Model, fields
from django.db.models.fields import DateTimeField, DecimalField, Field, UUIDField

from .code import Code
from .registry import get_class
from .serializable import Serializable

TZ = "__DATETIME__"
MODEL = "__MODEL__"
UUID_IDENTIFIER = "__UUID__"


TZ_IDX = {tz: idx for idx, tz in enumerate(sorted(pytz.common_timezones))}
TZ_VAL = {idx: pytz.timezone(tz) for tz, idx in TZ_IDX.items()}

logger = logging.getLogger(__name__)


def serialize_timezone(dt: datetime) -> int:
    return TZ_IDX[dt.tzinfo.zone]  # type: ignore


def serialize_dt(dt: datetime) -> tuple:
    return (TZ, TZ_IDX[dt.tzinfo.zone], dt.timestamp())  # type: ignore


def deserialize_dt(zone_id: int, timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp, TZ_VAL[zone_id])


def deserialize_model(
    class_id: Union[str, int], serialized_value: List[Any]
) -> Serializable:
    ModelClass = get_class(class_id)
    return ModelClass.from_tuple(serialized_value)


def _build_deserialization_expression(idx: int, field: Field, depth: int = 0) -> Code:
    code = Code()
    if field.is_relation:
        pk_field: Field = field.related_model._meta.pk
        code.add(f"if val[{idx}]:")
        if isinstance(pk_field, UUIDField):
            code.add(f"if isinstance(val[{idx}], bytes):")
            code.add(f"instance.{field.name}_id = UUID(bytes=val[{idx}])")
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
                f"instance.{field.name} = UUID(bytes=val[{idx}]) if isinstance(val[{idx}], bytes) else fields[{idx}].to_python(val[{idx}])"
            )
        elif isinstance(field, DateTimeField):
            code.add(f"instance.{field.name} = (")
            code.start_block()
            code.add("None")
            code.add(f"if val[{idx}] is None else")
            code.add(f"datetime.fromtimestamp(val[{idx}][1], TZ_VAL[val[{idx}][0]])")
            code.outdent()
            code.add(")")
            code.add_globals(datetime=datetime, TZ_VAL=TZ_VAL)
        else:
            code.add(f"instance.{field.name} = fields[{idx}].to_python(val[{idx}])")
    return code


def compile_to_tuple_function(ModelClass: Type[Model], serializers_dict: dict) -> None:
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
            code.add(null_check(f"val.{field.name}.bytes") + ",")
        elif isinstance(field, DecimalField):
            code.add(null_check(f"str(val.{field.name})") + ",")
        elif isinstance(field, DateTimeField):
            code.add(
                null_check(
                    f"(TZ_IDX[val.{field.name}.tzinfo.zone], val.{field.name}.timestamp())"
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
                f"val.{field.name}.to_tuple() if '{field.name}' in val._state.fields_cache else {id_expr},"
            )
        else:
            code.add(f"val.{field.name},")

    code.outdent()
    code.add(")")
    code.full_outdent()

    code.add(f"_SERIALIZERS[ModelClass] = {fn_name}")
    code.add_globals(_SERIALIZERS=serializers_dict)
    code.exec()


def compile_from_tuple_function(
    ModelClass: Type[Model], deserializers_dict: dict
) -> None:
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
    code.exec()
