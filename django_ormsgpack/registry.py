from zlib import adler32

CLASS_TO_ID = {}
ID_TO_CLASS = {}
ASCII = "ascii"

SERIALIZER_ID = "_serializer_id"


def class_fqname(klass) -> str:
    return klass.__module__ + "." + klass.__name__


def register_serializable(decorated):
    """
    Add the decorated class to registry of serializable classes.
    """
    id_num = adler32(class_fqname(decorated).encode(ASCII))
    ID_TO_CLASS[id_num] = decorated
    CLASS_TO_ID[decorated] = id_num
    setattr(decorated, SERIALIZER_ID, id_num)
    return decorated
