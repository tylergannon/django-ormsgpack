from __future__ import annotations
import decimal
from typing import Optional, Set, Any, Iterable, List
from django.db.models.fields import Field
from django.db.models import Model
import ormsgpack


def default(obj):
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    if isinstance(obj, SerializableModel):
        return obj.to_tuple()
    raise TypeError


def serialize(val):
    return ormsgpack.packb(val, default=default)


def deserialize(val):
    return ormsgpack.unpackb(val)


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

    def __get_field(
        self, field: Field, pk_only: Optional[Set[str]], load_related: bool
    ) -> Any:
        name = field.name
        if not field.is_relation:
            return getattr(self, name)
        if (pk_only and name in pk_only) or not (
            load_related or name in self._state.fields_cache  # pylint: disable=E1101
        ):
            return getattr(self, field.name + "_id")

        val = getattr(self, name)
        if isinstance(val, SerializableModel):
            return val.to_tuple(load_related)
        # Don't know how to serialize this, just provide the id.
        return getattr(self, field.name + "_id")

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
        obj = cls()
        for field, value in zip(cls.get_serializer_fields(), values):
            name = cls._deserialize_field_name(field, value)
            value = cls._deserialize_field_value(field, value)
            setattr(obj, name, value)

        obj._is_deserialized_copy = True

        return obj

    def to_tuple(self, load_related: Optional[bool] = None) -> tuple:
        """
        Convert the object to list based on configuration.
        """
        metadata = type(self).Serialize
        if load_related is None:
            load_related = getattr(metadata, "load_related", False)

        fields = type(self).get_serializer_fields()

        pk_only = getattr(metadata, "pk_only", None)
        return tuple(self.__get_field(field, pk_only, load_related) for field in fields)

    class Meta:
        abstract = True
