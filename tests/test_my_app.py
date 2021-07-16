from timeit import timeit
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from django_ormsgpack import __version__
from django.utils import timezone
from my_app.models import ATestModel, Ticket
from django_ormsgpack.serializer import serialize, deserialize
from django_ormsgpack.serializer_fns import serialize_timezone
from pickle import dumps, loads


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
    print(as_tuple)
    assert as_tuple[0] == pk_uuid.bytes
    assert as_tuple[1] == "Coolio"
    assert as_tuple[2][1] == now.timestamp()
    assert as_tuple[2][0] == serialize_timezone(now)
    assert as_tuple[3] == str(decimal_val)
    assert as_tuple[4] == 123
    assert as_tuple[5] == some_uuid.bytes

    other_model_instance = ATestModel.from_tuple(as_tuple)

    assert deserialize(other_model_instance.id) == model_instance.id
    assert other_model_instance.char_field == model_instance.char_field
    assert other_model_instance.int_field == model_instance.int_field
    assert other_model_instance.date_field == model_instance.date_field
    assert other_model_instance.zorg == model_instance.zorg
    assert other_model_instance.zorg2 != model_instance.zorg2


def test_make_ticket(model_b_instance):
    ticket = Ticket(
        screening=model_b_instance,
        user=model_b_instance,
        purchaser=model_b_instance,
        cnt_feature_views=12345,
        cnt_preroll_views=435212,
        cnt_postroll_views=23423,
        viewing_open_time=timezone.now(),
        viewing_close_time=timezone.now(),
    )
    pickled = dumps(ticket)
    zorg = loads(pickled)
    print("PLORK", zorg._state.fields_cache)
    print("ZORK", ticket.to_tuple())
    serialized = serialize(ticket)
    print("COOLIO", serialized)
    assert len(pickled) >= len(serialized) * 3


X = 500000


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


def test_sizes(model_b_instance, model_instance):
    print(f"Model A length: {len(serialize(model_b_instance))}")
    print(f"Model B length: {len(serialize(model_b_instance))}")
    print(f"Model B via Pickle: {len(dumps(model_b_instance))}")
