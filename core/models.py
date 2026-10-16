import uuid
from typing import Any

from django.db import models
from ulid import ULID, default_generator


def new_ulid() -> uuid.UUID:
    return default_generator.generate().to_uuid()


class ULIDField(models.UUIDField):
    def to_python(self, value: Any) -> uuid.UUID | None:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        text = str(value).strip()
        if not text:
            return None
        try:
            return ULID.parse(text).to_uuid()
        except ValueError:
            fallback = super().to_python(text)
            return None if fallback is None else uuid.UUID(str(fallback))

    def get_prep_value(self, value: Any) -> Any:
        if isinstance(value, ULID):
            value = value.to_uuid()
        return super().get_prep_value(value)


class TimestampedModel(models.Model):
    created_at = models.DateTimeField("Создано", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        abstract = True


class ULIDModel(models.Model):
    id = ULIDField("Идентификатор", primary_key=True, default=new_ulid, editable=False)

    class Meta:
        abstract = True


class BaseModel(ULIDModel, TimestampedModel):
    class Meta:
        abstract = True
