from __future__ import annotations

import decimal
import traceback
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
)

import ormsgpack
from django.db.models import Model
from django.db.models.fields import Field, UUIDField

from .serializable import Serializable
from .serializer_fns import compile_from_tuple_function, compile_to_tuple_function

T = TypeVar("T", bound=Serializable)

SerializerFunction = Callable[[Serializable], tuple]
DeserializerFunction = Callable[[Union[list, tuple]], Serializable]


_SERIALIZERS: Dict[Type[Serializable], SerializerFunction] = {}
_DESERIALIZERS: Dict[Type[Serializable], DeserializerFunction] = {}


class SerializationError(Exception):
    "Error during serialization."


class SerializationProgrammingError(SerializationError):
    "Programmer error in serialization code"


ERROR_UPDATE_FIELDS = "To save a deserialized copy of a model, the instance must either: (a) be of a class that is configured to serialize all of its fields, (b) provide `update_fields` with a subset of the serialized fields, or (c) provide `force_insert` or `force_update`."


@Serializable.register
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
        force_insert: bool = False,
        force_update: bool = False,
        update_fields: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Any:
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
            or len(type(self).serialized_field_names()) == len(self._meta.fields)
        ):
            return super().save(
                force_insert, force_update, update_fields=update_fields, **kwargs
            )
        if not update_fields or any(
            name
            for name in update_fields
            if name not in type(self).serialized_field_names()
        ):
            raise SerializationProgrammingError(ERROR_UPDATE_FIELDS)
        return super().save(
            force_insert, force_update, update_fields=update_fields, **kwargs
        )

    @classmethod
    def serialized_field_names(cls) -> Set[str]:
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
    def from_tuple(cls: T, values: Iterable[Any]) -> T:  # type: ignore
        """
        Build object from values created by `to_tuple`.
        """
        try:
            return _DESERIALIZERS[cls](values)  # type: ignore
        except KeyError:
            try:
                compile_from_tuple_function(cls, _DESERIALIZERS)  # type: ignore
                return cls.from_tuple(values)  # type: ignore
            except Exception as ex:
                traceback.print_exc()
                raise SerializationError() from ex

    @classmethod
    def deserialize(cls: T, val: bytes) -> T:  # type: ignore
        return cls.from_tuple(
            ormsgpack.unpackb(val)
        )  # pylint: disable=c-extension-no-member

    def to_tuple(self) -> tuple:
        """
        Convert the object to list based on configuration.
        """
        try:
            return _SERIALIZERS[self.__class__](self)
        except KeyError:
            try:
                compile_to_tuple_function(self.__class__, _SERIALIZERS)
                return self.to_tuple()
            except Exception as ex:
                traceback.print_exc()
                raise SerializationError() from ex

    def serialize(self) -> bytes:
        return ormsgpack.packb(self.to_tuple())

    class Meta:
        abstract = True
