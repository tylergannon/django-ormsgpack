from __future__ import annotations
from .serializable import Serializable
from typing import Union, Type
from zlib import adler32
from django.utils.module_loading import import_string

CLASS_TO_ID = {}
ID_TO_CLASS = {}
ASCII = "ascii"

SERIALIZER_ID = "_serializer_id"


def class_fqname(klass) -> str:
    "Return the dot-separated module and class name."
    return klass.__module__ + "." + klass.__name__


def get_class(class_fqn: Union[str, int]) -> Type[Serializable]:
    """
    Get a class either by dot-separated full module and class name, or by
    integer id.

    :param class_fqn: a dot-separated string name, or integer class_id as
                      created by the `register_serializable` decorator.
    """
    klass = ID_TO_CLASS.get(class_fqn)
    if not klass:
        klass = import_string(class_fqn)
        ID_TO_CLASS[class_fqn] = klass
    return klass


def register_serializable(decorated):
    """
    Add the decorated class to registry of serializable classes.
    """
    id_num = adler32(class_fqname(decorated).encode(ASCII))
    ID_TO_CLASS[id_num] = decorated
    CLASS_TO_ID[decorated] = id_num
    decorated._serializer_id = id_num
    return decorated
