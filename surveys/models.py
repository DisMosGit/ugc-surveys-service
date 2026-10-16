from django.db import models

from core.models import BaseModel
from surveys.enums import QuestionKind


class Survey(BaseModel):
    author = models.ForeignKey(
        "accounts.ApiUser",
        on_delete=models.PROTECT,
        related_name="surveys",
        verbose_name="Автор",
    )
    title = models.TextField("Название")
    description = models.TextField("Описание", blank=True, default="")
    is_active = models.BooleanField("Активен", default=True)
    version = models.PositiveIntegerField("Версия", default=1)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "опрос"
        verbose_name_plural = "опросы"
        indexes = [
            models.Index(fields=["author", "-created_at"], name="survey_author_created_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class Question(BaseModel):
    survey = models.ForeignKey(
        "surveys.Survey",
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name="Опрос",
    )
    text = models.TextField("Текст вопроса")
    order = models.PositiveIntegerField("Порядок")
    kind = models.PositiveSmallIntegerField(
        "Тип вопроса",
        choices=QuestionKind,
        default=QuestionKind.SINGLE_CHOICE,
    )
    allows_custom_answer = models.BooleanField("Разрешает свой вариант ответа", default=True)
    is_required = models.BooleanField("Обязательный", default=True)

    class Meta:
        ordering = ["order"]
        verbose_name = "вопрос"
        verbose_name_plural = "вопросы"
        constraints = [
            models.UniqueConstraint(fields=["survey", "order"], name="unique_question_order_per_survey"),
        ]

    def __str__(self) -> str:
        return f"{self.order}. {self.text[:80]}"


class AnswerOption(BaseModel):
    question = models.ForeignKey(
        "surveys.Question",
        on_delete=models.CASCADE,
        related_name="options",
        verbose_name="Вопрос",
    )
    text = models.TextField("Текст варианта ответа")
    order = models.PositiveSmallIntegerField("Порядок")
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        ordering = ["order"]
        verbose_name = "вариант ответа"
        verbose_name_plural = "варианты ответов"
        constraints = [
            models.UniqueConstraint(fields=["question", "order"], name="unique_option_order_per_question"),
        ]

    def __str__(self) -> str:
        return f"{self.order}. {self.text}"
