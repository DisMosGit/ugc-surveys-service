from datetime import datetime
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import BigIntegerField, Count, F, QuerySet, Value
from django.db.models.functions import Greatest
from django.utils import timezone

from analytics.models import OptionStatistics, QuestionStatistics, SurveyStatistics
from answers.enums import SessionStatus
from answers.models import Answer, SurveySession
from surveys.models import AnswerOption, Question

SURVEY_FIELDS = ["completed_count", "answers_count", "duration_sum_ms", "updated_at"]
QUESTION_FIELDS = ["answers_count", "updated_at"]
OPTION_FIELDS = ["selected_count", "updated_at"]


def record_session_completed(session: SurveySession) -> None:
    _bump(
        SurveyStatistics,
        {"survey_id": session.survey_id},
        {"completed_count": 1, "duration_sum_ms": _session_duration_ms(session)},
    )


def record_answer(
    *,
    survey_id: UUID,
    question_id: UUID,
    option_id: UUID | None,
    previous_option_id: UUID | None,
    created: bool,
) -> None:
    if created:
        _bump(SurveyStatistics, {"survey_id": survey_id}, {"answers_count": 1})
        _bump(QuestionStatistics, {"question_id": question_id}, {"answers_count": 1})
        if option_id is not None:
            _bump(OptionStatistics, {"option_id": option_id}, {"selected_count": 1})
        return
    if previous_option_id == option_id:
        return
    if previous_option_id is not None:
        _bump(OptionStatistics, {"option_id": previous_option_id}, {"selected_count": -1})
    if option_id is not None:
        _bump(OptionStatistics, {"option_id": option_id}, {"selected_count": 1})


def recalculate_survey(survey_id: UUID | str) -> None:
    with transaction.atomic():
        statistics, _ = SurveyStatistics.objects.select_for_update().get_or_create(survey_id=survey_id)
        sessions = SurveySession.objects.filter(survey_id=survey_id)
        statistics.completed_count = sessions.filter(status=SessionStatus.COMPLETED).count()
        statistics.answers_count = Answer.objects.filter(session__survey_id=survey_id).count()
        statistics.duration_sum_ms = _duration_sum(sessions)
        statistics.save(update_fields=SURVEY_FIELDS)
        _recalculate_questions(survey_id)
        _recalculate_options(survey_id)


def _recalculate_questions(survey_id: UUID | str) -> None:
    question_ids = list(Question.objects.filter(survey_id=survey_id).values_list("pk", flat=True))
    answers_count = _counts_by(Answer.objects.filter(question_id__in=question_ids), "question_id")
    existing = {
        row.question_id: row
        for row in QuestionStatistics.objects.filter(question_id__in=question_ids).order_by("pk")
    }
    fresh: list[QuestionStatistics] = []
    for question_id in question_ids:
        row = existing.get(question_id)
        if row is None:
            row = QuestionStatistics(question_id=question_id)
            fresh.append(row)
        row.answers_count = answers_count.get(question_id, 0)
        row.updated_at = timezone.now()
    if fresh:
        QuestionStatistics.objects.bulk_create(fresh)
    if existing:
        QuestionStatistics.objects.bulk_update(list(existing.values()), QUESTION_FIELDS)


def _recalculate_options(survey_id: UUID | str) -> None:
    option_ids = list(AnswerOption.objects.filter(question__survey_id=survey_id).values_list("pk", flat=True))
    selected_count = _counts_by(Answer.objects.filter(option_id__in=option_ids), "option_id")
    existing = {
        row.option_id: row for row in OptionStatistics.objects.filter(option_id__in=option_ids).order_by("pk")
    }
    fresh: list[OptionStatistics] = []
    for option_id in option_ids:
        row = existing.get(option_id)
        if row is None:
            row = OptionStatistics(option_id=option_id)
            fresh.append(row)
        row.selected_count = selected_count.get(option_id, 0)
        row.updated_at = timezone.now()
    if fresh:
        OptionStatistics.objects.bulk_create(fresh)
    if existing:
        OptionStatistics.objects.bulk_update(list(existing.values()), OPTION_FIELDS)


def _counts_by(queryset: QuerySet[Answer], field: str) -> dict[Any, int]:
    rows = queryset.values(field).annotate(total=Count("id"))
    return {row[field]: row["total"] for row in rows}


def _duration_sum(sessions: QuerySet[SurveySession]) -> int:
    pairs = sessions.filter(status=SessionStatus.COMPLETED, completed_at__isnull=False).values_list(
        "created_at", "completed_at"
    )
    return sum(_elapsed_ms(started_at, finished_at) for started_at, finished_at in pairs)


def _session_duration_ms(session: SurveySession) -> int:
    return _elapsed_ms(session.created_at, session.completed_at)


def _elapsed_ms(started_at: datetime, finished_at: datetime | None) -> int:
    if finished_at is None:
        return 0
    return max(int((finished_at - started_at).total_seconds() * 1000), 0)


def _bump(model: type[Any], lookup: dict[str, Any], increments: dict[str, int]) -> None:
    expressions = {name: _counter(name, delta) for name, delta in increments.items() if delta}
    if not expressions:
        return
    if model.objects.filter(**lookup).update(**expressions, updated_at=timezone.now()):
        return
    defaults: dict[str, Any] = {name: delta for name, delta in increments.items() if delta > 0}
    defaults["updated_at"] = timezone.now()
    _, created = model.objects.get_or_create(**lookup, defaults=defaults)
    if not created:
        model.objects.filter(**lookup).update(**expressions, updated_at=timezone.now())


def _counter(name: str, delta: int) -> Any:
    return Greatest(F(name) + delta, Value(0), output_field=BigIntegerField())
