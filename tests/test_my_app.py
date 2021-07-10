from timeit import timeit
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from django_ormsgpack import __version__
from my_app.models import ATestModel
from django_ormsgpack.serializer import serialize
from pickle import dumps


def test_version():
    assert __version__ == "0.1.0"


def test_to_tuple(
    model_instance: ATestModel,
    some_uuid: UUID,
    pk_uuid: UUID,
    now: datetime,
    decimal_val: Decimal,
):
    as_tuple = model_instance.to_tuple()
    assert as_tuple == (pk_uuid, "Coolio", now, decimal_val, 123, some_uuid)

    other_model_instance = ATestModel.from_tuple(as_tuple)

    assert other_model_instance.id == model_instance.id
    assert other_model_instance.char_field == model_instance.char_field
    assert other_model_instance.int_field == model_instance.int_field
    assert other_model_instance.date_field == model_instance.date_field
    assert other_model_instance.zorg == model_instance.zorg
    assert other_model_instance.zorg2 != model_instance.zorg2


X = 100000


def test_timings_a(model_instance):
    fast = timeit(lambda: serialize(model_instance), number=X)
    print(f"FAST: {fast}")
    slow = timeit(lambda: dumps(model_instance), number=X)
    print(f"SLOW: {slow}")


def test_timings_b(model_b_instance):
    fast = timeit(lambda: serialize(model_b_instance), number=X)
    print(f"FAST: {fast}")
    slow = timeit(lambda: dumps(model_b_instance), number=X)
    print(f"SLOW: {slow}")


def test_timings_tuple(model_b_instance, model_instance):
    zorgoth = model_instance.to_tuple()
    zilgor = model_b_instance.to_tuple()
    fast = timeit(lambda: serialize(zilgor), number=X)
    print(f"FAST: {fast} / size: {len(serialize(model_b_instance))}")
    print("Compare")
    print(serialize(model_instance))
    print(serialize(model_b_instance))
    print(len(serialize(model_instance)))
    print(len(serialize(model_b_instance)))
    slow = timeit(lambda: dumps(zilgor), number=X)
    print("⤴")
    print(
        f"SLOW: {slow} / size: {len(dumps(model_b_instance))}😗{dumps(model_b_instance)}😗"
    )
