from django.db import models
from django.db.models import Q

from answers.enums import SessionStatus
from core.models import BaseModel


class SurveySession(BaseModel):
    survey = models.ForeignKey(
        "surveys.Survey",
        on_delete=models.CASCADE,
        related_name="sessions",
        verbose_name="Опрос",
    )
    user = models.ForeignKey(
        "accounts.ApiUser",
        on_delete=models.CASCADE,
        related_name="sessions",
        verbose_name="Пользователь",
    )
    status = models.PositiveSmallIntegerField("Статус", choices=SessionStatus, default=SessionStatus.ACTIVE)
    survey_version = models.PositiveIntegerField("Версия опроса", default=1)
    last_answered_order = models.PositiveIntegerField("Порядок последнего отвеченного вопроса", default=0)
    answered_count = models.PositiveIntegerField("Количество ответов", default=0)
    completed_at = models.DateTimeField("Завершено в", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "прохождение опроса"
        verbose_name_plural = "прохождения опросов"
        constraints = [
            models.UniqueConstraint(
                fields=["survey", "user"],
                condition=Q(status=SessionStatus.ACTIVE),
                name="unique_active_session_per_user_survey",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="session_user_created_idx"),
            models.Index(fields=["survey", "status"], name="session_survey_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user} — {self.survey} ({self.get_status_display()})"


class Answer(BaseModel):
    session = models.ForeignKey(
        "answers.SurveySession",
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="Прохождение",
    )
    question = models.ForeignKey(
        "surveys.Question",
        on_delete=models.PROTECT,
        related_name="answers",
        verbose_name="Вопрос",
    )
    option = models.ForeignKey(
        "surveys.AnswerOption",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="answers",
        verbose_name="Вариант ответа",
    )
    custom_text = models.TextField("Свой вариант ответа", blank=True, default="")

    class Meta:
        ordering = []
        verbose_name = "ответ"
        verbose_name_plural = "ответы"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "question"], name="unique_answer_per_session_question"
            ),
            models.CheckConstraint(
                condition=Q(option__isnull=False, custom_text="")
                | Q(option__isnull=True) & ~Q(custom_text=""),
                name="answer_has_single_source",
            ),
        ]

    def __str__(self) -> str:
        return self.custom_text or str(self.option)
