from django.contrib.auth.models import AbstractUser
from django.db import models

from accounts.enums import UserRole
from core.models import BaseModel, TimestampedModel

MIN_UNSAFE_ID = 1
MAX_UNSAFE_ID = 2**63 - 1


class AdminUser(AbstractUser, TimestampedModel):
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "административный пользователь"
        verbose_name_plural = "административные пользователи"


class ApiUser(BaseModel):
    unsafe_id = models.PositiveBigIntegerField("Небезопасный идентификатор", unique=True)
    role = models.PositiveSmallIntegerField("Роль", choices=UserRole, default=UserRole.PASSING)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "API-пользователь"
        verbose_name_plural = "API-пользователи"

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def __str__(self) -> str:
        return f"API-пользователь {self.unsafe_id}"
