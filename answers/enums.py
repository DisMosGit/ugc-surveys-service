from django.db import models


class SessionStatus(models.IntegerChoices):
    ACTIVE = 1, "Активно"
    COMPLETED = 2, "Завершено"
