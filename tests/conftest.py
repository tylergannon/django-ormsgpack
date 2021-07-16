"Fixtures and stuff"
import pytest
from random import randint
from uuid import uuid4
from decimal import Decimal
from django.utils import timezone
from my_app.models import ATestModel, BTestModel, CTestModel, Ticket


@pytest.fixture
def pk_uuid():
    return uuid4()


@pytest.fixture
def some_uuid():
    return uuid4()


@pytest.fixture
def some_int():
    return randint(12, 1234567890)


@pytest.fixture
def now():
    return timezone.now()


@pytest.fixture
def decimal_val():
    return Decimal("20.22")


@pytest.fixture
def model_instance(pk_uuid, some_uuid, now, decimal_val):
    return ATestModel(
        id=pk_uuid,
        char_field="Coolio",
        date_field=now,
        decimal_field=decimal_val,
        int_field=123,
        zorg=some_uuid,
        zorg2=uuid4(),
    )


@pytest.fixture
def model_b_instance(pk_uuid, some_uuid, now, decimal_val):
    return BTestModel(
        id=pk_uuid,
        char_field="Coolio",
        date_field=now,
        decimal_field=decimal_val,
        int_field=123,
        zorg=some_uuid,
        zorg2=uuid4(),
    )


@pytest.fixture
def model_c_instance(some_int, some_uuid, now, decimal_val):
    return CTestModel(
        id=some_int,
        char_field="Coolio",
        date_field=now,
        decimal_field=decimal_val,
        int_field=123,
        zorg=some_uuid,
        zorg2=uuid4(),
    )


@pytest.fixture
def ticket_instance(model_b_instance, model_c_instance):
    return Ticket(
        screening=model_b_instance,
        user=model_b_instance,
        purchaser=model_c_instance,
        cnt_feature_views=12345,
        cnt_preroll_views=435212,
        cnt_postroll_views=23423,
        viewing_open_time=timezone.now(),
        viewing_close_time=timezone.now(),
    )
