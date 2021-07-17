from __future__ import annotations

from typing import Dict, Type, TypeVar, Union
from zlib import adler32

from django.db.models import Model
from django.utils.module_loading import import_string

from .serializable import Serializable

CLASS_TO_ID: Dict[Type[Serializable], int] = {}
ID_TO_CLASS: Dict[Union[int, str], Type[Serializable]] = {}
ASCII = "ascii"

SERIALIZER_ID = "_serializer_id"


def class_fqname(klass: Type[Serializable]) -> str:
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
        if klass is None:
            raise ValueError(f"I don't recognize {class_fqn}.")
        ID_TO_CLASS[class_fqn] = klass
    return klass


R = TypeVar("R", bound=Model)


def serializable_model(decorated: R) -> Union[R, Serializable]:
    """
    Add the decorated class to registry of serializable classes.
    """
    if not issubclass(decorated, Serializable):
        from .model import SerializableModel

        app_label = decorated._meta.app_label
        MetaSubclass = getattr(decorated, "Meta", object)

        app_models = decorated._meta.apps.all_models[decorated._meta.app_label]
        if decorated._meta.model_name in app_models:
            del app_models[decorated._meta.model_name]

        ModelClass = type(
            decorated.__name__,
            (
                SerializableModel,
                decorated,
            ),
            {
                "Meta": type(
                    "Meta",
                    (MetaSubclass,),
                    {"app_label": decorated._meta.app_label, "proxy": True},
                ),
                "__module__": decorated.__module__,
            },
        )

        # class ModelClass(SerializableModel, decorated):  # type: ignore
        #     class Meta(MetaSubclass):  # type: ignore
        #         app_label = decorated._meta.app_label

        ModelClass.__doc__ = decorated.__doc__
        decorated = ModelClass  # type: ignore
        Serializable.register(decorated)  # type: ignore

    id_num = adler32(class_fqname(decorated).encode(ASCII))
    ID_TO_CLASS[id_num] = decorated
    CLASS_TO_ID[decorated] = id_num
    decorated._serializer_id = id_num
    return decorated
