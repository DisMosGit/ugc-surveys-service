from django.db import models


class UserRole(models.IntegerChoices):
    PASSING = 1, "Участник"
    AUTHOR = 2, "Автор"
