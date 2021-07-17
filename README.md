# django-ormsgpack

**the missing Model serializer for Django cache and celery.**

`django-ormsgpack` provides serialization of Django Model class instances,
backed by [ormsgpack](https://github.com/aviramha/ormsgpack), resulting in serialization
far faster than [pickle](https://docs.python.org/dev/library/pickle.html#module-pickle),
and much smaller serialized values than pickle provides.


## Installation

```
pip install django-ormsgpack
```

## Mark up your models

```
from django.db import Models
from django_ormsgpack import serializable_model

@serializable_model
class MyModel(models.Model):
   class Serialize:
       pass



```
