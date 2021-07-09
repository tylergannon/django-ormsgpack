from __future__ import annotations
import decimal
from typing import Optional, Set, Any, Iterable, List
from django.db.models.fields import Field
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


class SerializableModel:
    @classmethod
    def loads(cls, serialized: str) -> cls:
        return cls.from_tuple(unpackb(serialized))

    def dumps(self, load_related: Optional[bool] = None) -> str:
        return packb(self.to_tuple(load_related))

    @classmethod
    def get_serializer_fields(cls) -> List[Field]:
        if hasattr(cls, '_serializer_fields'):
            return cls._serializer_fields

        try:
            metadata = cls.Serialize
        except AttributeError:
            raise SerializationProgrammingError('No Serialize class defined on the model.')

        fields = cls._meta.fields
        if hasattr(metadata, 'fields'):
            fields = [field for field in fields if field.name in metadata.fields or field is cls._meta.pk]

        setattr(cls, '_serializer_fields', fields)
        return fields

    def __get_field(self, field: Field, pk_only: Optional[Set[str]], load_related: bool) -> Any:
        name = field.name
        if not field.is_relation:
            return getattr(self, name)
        if (pk_only and name in pk_only) or not (load_related or name in self._state.fields_cache):
            return getattr(self, field.name + '_id')

        val = getattr(self, name)
        if isinstance(val, SerializableModel):
            return val.to_tuple(load_related)
        # Don't know how to serialize this, just provide the id.
        return getattr(self, field.name + '_id')

    @classmethod
    def _deserialize_field_name(cls, field: Field, val: Any) -> str:
        if field.name == cls._meta.pk.name:
            return 'pk'
        if field.is_relation and not isinstance(val, (tuple, list)):
            return field.name + '_id'
        return field.name

    @classmethod
    def _deserialize_field_value(cls, field: Field, val: Any):
        if not field.is_relation:
            return field.to_python(val)

        if isinstance(val, (tuple, list)):
            if issubclass(field.related_model, SerializableModel):
                return field.related_model.from_tuple(val)
            raise SerializationError('Tried to deserialize a {field.related_model} which is not serializable')

        # If it's a scalar value and a relation, we assume it's just the PK we're deserializing.
        return field.related_model._meta.pk.to_python(val)


    @classmethod
    def from_tuple(cls, values: Iterable[Any]) -> cls:
        obj = cls()
        for field, value in zip(cls.get_serializer_fields(), values):
            name = cls._deserialize_field_name(field, value)
            value = cls._deserialize_field_value(field, value)
            setattr(obj, name, value)

        return obj

    def to_tuple(self, load_related: Optional[bool] = None) -> tuple:
        """
        Convert the object to list based on configuration.
        """
        metadata = type(self).Serialize
        if load_related is None:
            load_related = getattr(metadata, 'load_related', False)

        fields = type(self).get_serializer_fields()

        pk_only = getattr(metadata, 'pk_only', None)
        return tuple(self.__get_field(field, pk_only, load_related) for field in fields)


