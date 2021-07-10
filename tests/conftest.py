"Fixtures and stuff"
import pytest
from uuid import uuid4
from decimal import Decimal
from django.utils import timezone
from my_app.models import ATestModel, BTestModel


@pytest.fixture
def pk_uuid():
    return uuid4()


@pytest.fixture
def some_uuid():
    return uuid4()


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
    )
