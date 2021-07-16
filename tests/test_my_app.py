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

    assert other_model_instance.char_field == model_instance.char_field
    assert other_model_instance.int_field == model_instance.int_field
    assert other_model_instance.date_field == model_instance.date_field
    assert other_model_instance.zorg == model_instance.zorg
    assert other_model_instance.zorg2 != model_instance.zorg2


def test_make_ticket(model_b_instance, model_c_instance):
    ticket = Ticket(
        screening=model_b_instance,
        user=model_b_instance,
        purchaser=model_c_instance,
        cnt_feature_views=12345,
        cnt_preroll_views=435212,
        cnt_postroll_views=23423,
        viewing_open_time=timezone.now(),
        viewing_close_time=timezone.now(),
    )
    pickled = dumps(ticket)
    serialized = serialize(ticket)
    assert len(pickled) >= len(serialized) * 3
    same_ticket: Ticket = deserialize(serialized)
    assert same_ticket.id == ticket.id
    assert same_ticket.cnt_feature_views == ticket.cnt_feature_views
    assert same_ticket.cnt_preroll_views == ticket.cnt_preroll_views
    assert same_ticket.cnt_postroll_views == ticket.cnt_postroll_views
    assert same_ticket.viewing_open_time == ticket.viewing_open_time
    assert same_ticket.viewing_close_time == ticket.viewing_close_time

    model_left = same_ticket.screening
    model_right = ticket.screening

    assert model_left.id == model_right.id
    assert model_left.char_field == model_right.char_field
    assert model_left.date_field == model_right.date_field
    assert model_left.decimal_field == model_right.decimal_field
    assert model_left.int_field == model_right.int_field
    assert model_left.zorg == model_right.zorg
    assert model_left.zorg2 is None

    model_left = same_ticket.user
    model_right = ticket.user

    assert model_left.id == model_right.id
    assert model_left.char_field == model_right.char_field
    assert model_left.date_field == model_right.date_field
    assert model_left.decimal_field == model_right.decimal_field
    assert model_left.int_field == model_right.int_field
    assert model_left.zorg == model_right.zorg
    assert model_left.zorg2 is None

    model_left = same_ticket.purchaser
    model_right = ticket.purchaser

    assert model_left.id == model_right.id
    assert model_left.char_field == model_right.char_field
    assert model_left.date_field == model_right.date_field
    assert model_left.decimal_field == model_right.decimal_field
    assert model_left.int_field == model_right.int_field
    assert model_left.zorg == model_right.zorg
    assert model_left.zorg2 is None

    # char_field = CharField(max_length=255)
    # date_field = DateTimeField()
    # decimal_field = DecimalField()
    # int_field = IntegerField()
    # zorg = UUIDField(default=uuid4)
    # zorg2 = UUIDField(default=uuid4)


def test_serialize_deserialize(model_b_instance, model_c_instance):
    ticket = Ticket(
        screening=model_b_instance,
        user=model_b_instance,
        purchaser=model_c_instance,
        cnt_feature_views=12345,
        cnt_preroll_views=435212,
        cnt_postroll_views=23423,
        viewing_open_time=timezone.now(),
        viewing_close_time=timezone.now(),
    )
    serialized = serialize(ticket)
    dumped = dumps(ticket)
    assert len(serialized) < len(dumped) / 3


X = 50000


def test_larger_deserialization(model_b_instance, model_c_instance, ticket_instance):
    the_value = [
        {
            "sauce": 12345,
            "x": 94322,
            "rightnow": timezone.now(),
            "1234": "awesome",
            "nested": [model_b_instance, model_c_instance],
        },
        ticket_instance,
    ]
    serialized = serialize(the_value)
    dumped = dumps(the_value)
    assert len(serialized) < len(dumped) / 2
    fast = timeit(lambda: serialize(the_value), number=X)
    print(f"FAST: {fast}")
    slow = timeit(lambda: dumps(the_value), number=X)
    print(f"SLOW: {slow}")
    assert fast < slow


def test_timings_a(model_instance):
    fast = timeit(lambda: serialize(model_instance), number=X)
    print(f"FAST: {fast}")
    slow = timeit(lambda: dumps(model_instance), number=X)
    print(f"SLOW: {slow}")
    assert fast < slow / 3


def test_timings_b(model_b_instance):
    fast = timeit(lambda: serialize(model_b_instance), number=X)
    print(f"FAST: {fast}")
    slow = timeit(lambda: dumps(model_b_instance), number=X)
    print(f"SLOW: {slow}")
    assert fast < slow / 3


def test_sizes(model_b_instance, model_instance):
    assert len(serialize(model_b_instance)) < len(dumps(model_b_instance)) / 3
    print(f"Model A length: {len(serialize(model_b_instance))}")
    print(f"Model B length: {len(serialize(model_b_instance))}")
    print(f"Model B via Pickle: {len(dumps(model_b_instance))}")
