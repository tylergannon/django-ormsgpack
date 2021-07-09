from uuid import uuid4
from django_ormsgpack import __version__
from django.db.models import (
    DateTimeField,
    DecimalField,
    IntegerField,
    CharField,
    Model,
    UUIDField,
)
from django_ormsgpack import SerializableModel


class ATestModel(Model, SerializableModel):
    id = UUIDField(primary_key=True, default=uuid4, editable=False)
    char_field = CharField(max_length=255)
    date_field = DateTimeField()
    decimal_field = DecimalField()
    int_field = IntegerField()
    zorg = UUIDField(default=uuid4)
    zorg2 = UUIDField(default=uuid4)

    class Serialize:
        fields = {"char_field", "date_field", "decimal_field", "int_field", "zorg"}
