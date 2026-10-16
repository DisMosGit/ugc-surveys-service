from django.db import models

from core.models import BaseModel


class SurveyStatistics(BaseModel):
    survey = models.OneToOneField(
        "surveys.Survey",
        on_delete=models.CASCADE,
        related_name="statistics",
        verbose_name="Опрос",
    )
    started_count = models.PositiveBigIntegerField("Начато", default=0)
    completed_count = models.PositiveBigIntegerField("Завершено", default=0)
    abandoned_count = models.PositiveBigIntegerField("Прервано", default=0)
    answers_count = models.PositiveBigIntegerField("Ответов", default=0)
    duration_sum_ms = models.BigIntegerField("Суммарная длительность, мс", default=0)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "статистика опроса"
        verbose_name_plural = "статистика опросов"

    def __str__(self) -> str:
        return f"{self.survey}: {self.completed_count} завершено"


class QuestionStatistics(BaseModel):
    question = models.OneToOneField(
        "surveys.Question",
        on_delete=models.CASCADE,
        related_name="statistics",
        verbose_name="Вопрос",
    )
    answers_count = models.PositiveBigIntegerField("Ответов", default=0)
    skipped_count = models.PositiveBigIntegerField("Пропущено", default=0)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "статистика вопроса"
        verbose_name_plural = "статистика вопросов"

    def __str__(self) -> str:
        return f"{self.question}: {self.answers_count} ответов"


class OptionStatistics(BaseModel):
    option = models.OneToOneField(
        "surveys.AnswerOption",
        on_delete=models.CASCADE,
        related_name="statistics",
        verbose_name="Вариант ответа",
    )
    selected_count = models.PositiveBigIntegerField("Выбрано", default=0)
    custom_answers_count = models.PositiveBigIntegerField("Своих ответов", default=0)

    class Meta:
        ordering = ["-selected_count"]
        verbose_name = "статистика варианта ответа"
        verbose_name_plural = "статистика вариантов ответов"

    def __str__(self) -> str:
        return f"{self.option}: {self.selected_count} выборов"
