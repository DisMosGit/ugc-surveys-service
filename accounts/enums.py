from django.db import models


class UserRole(models.IntegerChoices):
    PASSING = 1, "Прохождение"
    AUTHOR = 2, "Автор опросов"
