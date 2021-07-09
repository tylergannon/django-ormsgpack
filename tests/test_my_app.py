from timeit import timeit
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from django_ormsgpack import __version__
from my_app.models import ATestModel, BTestModel
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


class Model:
    def bork(self, x):
        return x * 9

    def save(self):
        return 952


class Sauce(Model):
    def bork(self, x):
        return x * 22


class Serializer(Model):
    def save(self):
        return 100


class Gorky(Sauce, Serializer):
    ...


def test_timings(model_b_instance):
    fast = timeit(lambda: serialize(model_b_instance), number=100000)
    print(f"FAST: {fast}")
    slow = timeit(lambda: dumps(model_b_instance), number=100000)
    print(f"SLOW: {slow}")
