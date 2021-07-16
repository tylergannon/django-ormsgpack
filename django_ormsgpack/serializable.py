from __future__ import annotations
from typing import List, Any, NewType, Type, TypeVar
from abc import ABC, abstractmethod


class Serializable(ABC):
    _serializer_id = 0

    @classmethod
    @abstractmethod
    def from_tuple(cls: Type[T], val: List[Any]) -> T:
        """
        Build an object from the serialized values given.
        """

    @abstractmethod
    def to_tuple(self) -> tuple:
        """
        Serializes the object to a ormsgpack-compatible tuple of values.
        """


T = TypeVar("T", bound=Serializable)
