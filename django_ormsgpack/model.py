from __future__ import annotations
import traceback
import decimal
from typing import Optional, Set, Any, Iterable, List, Union, Type
from django.db.models.fields import Field, UUIDField
from django.db.models import Model
from .serializer_fns import serialize_dt, wrap_expr, compile_from_tuple_function
import ormsgpack

_ignore = serialize_dt

TO_TUPLE_TEMPLATE = """
def to_tuple(model):
    return ({expressions})

_SERIALIZERS[ModelClass] = to_tuple
"""


UUID_FK_SETTER = """
if {val_name}[{idx}][0] == '{MODEL}'
"""

_SERIALIZERS = {}
_DESERIALIZERS = {}

INDENT = "    "


class SerializationError(Exception):
    "Error during serialization."


class SerializationProgrammingError(SerializationError):
    "Programmer error in serialization code"


ERROR_UPDATE_FIELDS = "To save a deserialized copy of a model, the instance must either: (a) be of a class that is configured to serialize all of its fields, (b) provide `update_fields` with a subset of the serialized fields, or (c) provide `force_insert` or `force_update`."


class SerializableModel(Model):
    """
    Enables serialization with django_ormsgpack.
    """

    # @classmethod
    # def loads(cls, serialized: str) -> cls:
    #     return cls.from_tuple(unpackb(serialized))

    # def dumps(self, load_related: Optional[bool] = None) -> str:
    #     return packb(self.to_tuple(load_related))
    _serializer_fields: Optional[List[Field]] = None
    _serializer_names: Optional[Set[str]] = None
    _serializer_id: Optional[int] = None

    _is_deserialized_copy: bool = False

    def save(
        self,
        force_insert=False,
        force_update=False,
        update_fields=None,
        **kwargs,
    ):
        """
        Save the model.  Raises `SerializationProgrammingError` if save() would
        corrupt the database by saving empty values for unserialized fields on
        instances that have been deserialized prior to saving, unless one of the
        `force` options is provided.

        It is recommended, whenever saving an object that has been deserialized,
        to provide `update_fields` with a list of fields to update, or else
        circumvent this method by calling `ModelClass.objects.filter(...).update(...)`
        """
        if (
            (not self._is_deserialized_copy)
            or force_insert
            or force_update
            or self.pk is None
            or len(type(self)._serialized_field_names()) == len(self._meta.fields)
        ):
            return super().save(
                force_insert, force_update, update_fields=update_fields, **kwargs
            )
        if not update_fields or any(
            name
            for name in update_fields
            if name not in type(self)._serialized_field_names()
        ):
            raise SerializationProgrammingError(ERROR_UPDATE_FIELDS)
        return super().save(
            force_insert, force_update, update_fields=update_fields, **kwargs
        )

    def _to_tuple(self) -> Optional[Iterable[Any]]:  # pylint: disable=R0201
        "Does the actual work serializing object to tuple."
        return None

    @classmethod
    def _serialized_field_names(cls) -> Set[str]:
        "Set of names of fields to be serialized"
        if cls._serialized_field_names is not None:
            return cls._serialized_field_names
        cls._serialized_field_names = {
            field.name for field in cls.get_serializer_fields()
        }
        return cls._serialized_field_names

    @classmethod
    def get_serializer_fields(cls) -> List[Field]:
        if cls._serializer_fields is not None:
            return cls._serializer_fields

        try:
            metadata = cls.Serialize
        except AttributeError:
            raise SerializationProgrammingError(
                "No Serialize class defined on the model."
            ) from None

        fields = cls._meta.fields  # pylint: disable=E1101
        if hasattr(metadata, "fields"):
            fields = [
                field
                for field in fields
                if field.name in metadata.fields
                or field is cls._meta.pk  # pylint: disable=E1101
            ]
        cls._serializer_fields = fields
        return fields

    @classmethod
    def _deserialize_field_name(cls, field: Field, val: Any) -> str:
        if field.name == cls._meta.pk.name:  # pylint: disable=E1101
            return "pk"
        if field.is_relation and not isinstance(val, (tuple, list)):
            return field.name + "_id"
        return field.name

    @classmethod
    def _deserialize_field_value(cls, field: Field, val: Any):
        if not field.is_relation:
            return field.to_python(val)

        if isinstance(val, (tuple, list)):
            if issubclass(field.related_model, SerializableModel):
                return field.related_model.from_tuple(val)
            raise SerializationError(
                "Tried to deserialize a {field.related_model} which is not serializable"
            )

        # If it's a scalar value and a relation, we assume it's just the PK we're deserializing.
        return field.related_model._meta.pk.to_python(val)

    @classmethod
    def from_tuple(cls, values: Iterable[Any]) -> cls:
        """
        Build object from values created by `to_tuple`.
        """
        try:
            return _DESERIALIZERS[cls](values)
        except KeyError:
            try:
                compile_from_tuple_function(cls, _DESERIALIZERS)
                return cls.from_tuple(values)
            except Exception as ex:
                raise SerializationError() from ex

    @classmethod
    def register_deserializer(cls, fn):
        _DESERIALIZERS[cls] = fn

    def to_tuple(self) -> tuple:
        """
        Convert the object to list based on configuration.
        """
        try:
            return _SERIALIZERS[self.__class__](self)
        except KeyError:
            try:
                return self.__define_to_tuple()
            except Exception as ex:
                raise SerializationError() from ex

    @classmethod
    def __define_from_tuple(cls):
        metadata = cls.Serialize  # pylint: disable=E1101
        fields = cls.get_serializer_fields()
        expressions = []
        for idx, field in enumerate(fields):
            if field.is_relation:
                if isinstance(field.related_model._meta.pk, UUIDField):
                    expr = f"setattr(model, )"
                    expr = f"'{field.name}_id': (UUID(bytes=val[{idx}][1]) if val[{idx}][0] == '{UUID_IDENTIFIER}')"

    def __define_to_tuple(self) -> List[Any]:
        "Define a _to_tuple method and attach it to the class."
        metadata = type(self).Serialize  # pylint: disable=E1101
        load_related: bool = getattr(metadata, "load_related", False)

        fields = type(self).get_serializer_fields()
        pk_only: Set[str] = getattr(metadata, "pk_only", set())
        expressions = []
        for field in fields:
            if not field.is_relation or field.name not in pk_only and load_related:
                expressions.append(wrap_expr(f"model.{field.name}", field))
            elif field.name in pk_only:
                expressions.append(f"model.{field.name}_id")
            else:
                expressions.append(
                    wrap_expr(f"model.{field.name}", field)
                    + f" if '{field.name}' in model._state.fields_cache"
                    f" else model.{field.name}_id"
                )
        ModelClass = self.__class__
        function = TO_TUPLE_TEMPLATE.format(expressions=", ".join(expressions))
        exec(  # pylint: disable=W0122
            compile(function, "<string>", "exec"),
            {"serialize_dt": serialize_dt},
            {"_SERIALIZERS": _SERIALIZERS, "ModelClass": ModelClass},
        )
        return _SERIALIZERS[self.__class__](self)

    class Meta:
        abstract = True
