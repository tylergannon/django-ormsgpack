from uuid import uuid4
from django.db import models
from django.db.models import (
    DateTimeField,
    DecimalField,
    IntegerField,
    CharField,
    Model,
    UUIDField,
)
from django_ormsgpack import serializable_model


@serializable_model
class ATestModel(Model):
    id = UUIDField(primary_key=True, default=uuid4, editable=False)
    char_field = CharField(max_length=255)
    date_field = DateTimeField()
    decimal_field = DecimalField()
    int_field = IntegerField()
    zorg = UUIDField()
    zorg2 = UUIDField()

    class Serialize:
        fields = {"char_field", "date_field", "decimal_field", "int_field", "zorg"}


@serializable_model
class BTestModel(ATestModel):
    ...


@serializable_model
class CTestModel(BTestModel):
    id = IntegerField(primary_key=True)


@serializable_model
class Ticket(Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    screening = models.ForeignKey(
        BTestModel, related_name="screenings", on_delete=models.PROTECT
    )
    user = models.ForeignKey(BTestModel, related_name="users", on_delete=models.PROTECT)
    purchaser = models.ForeignKey(
        CTestModel, related_name="sauce", on_delete=models.PROTECT
    )
    cnt_feature_views = models.IntegerField(default=0)
    cnt_preroll_views = models.IntegerField(default=0)
    cnt_postroll_views = models.IntegerField(default=0)
    viewing_open_time = models.DateTimeField()
    viewing_close_time = models.DateTimeField()
    subscribed = models.BooleanField(default=False, null=False, blank=False)

    class Serialize:
        ...
