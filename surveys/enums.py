from django.db import models


class QuestionKind(models.IntegerChoices):
    SINGLE_CHOICE = 1, "Одиночный выбор"
    TEXT = 2, "Свободный ответ"
