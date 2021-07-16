from timeit import timeit
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from django_ormsgpack import __version__
from my_app.models import ATestModel
from django_ormsgpack.serializer_fns import (
    compile_from_tuple_function,
    compile_to_tuple_function,
)
from pickle import dumps


def test_to_tuple_fn():
    gorky = {}
    compile_to_tuple_function(ATestModel, gorky)
    print("TO_TUPLE", gorky)


def test_from_tuple_fn():
    gorky = {}
    compile_from_tuple_function(ATestModel, gorky)
    print("FROM_TUPLE", gorky)
