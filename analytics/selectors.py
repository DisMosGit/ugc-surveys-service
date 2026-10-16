from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from analytics.models import OptionStatistics, QuestionStatistics, SurveyStatistics
from surveys.models import Survey


@dataclass(frozen=True)
class OptionBreakdown:
    id: UUID
    text: str
    order: int
    selected_count: int
    updated_at: datetime


@dataclass(frozen=True)
class QuestionBreakdown:
    id: UUID
    text: str
    order: int
    answers_count: int
    updated_at: datetime
    options: list[OptionBreakdown]


@dataclass(frozen=True)
class SurveyBreakdown:
    survey: Survey
    statistics: SurveyStatistics | None
    questions: list[QuestionBreakdown]


def survey_breakdown(survey: Survey) -> SurveyBreakdown:
    options = _options_by_question(survey)
    questions = [
        QuestionBreakdown(
            id=row.question_id,
            text=row.question.text,
            order=row.question.order,
            answers_count=row.answers_count,
            updated_at=row.updated_at,
            options=options.get(row.question_id, []),
        )
        for row in QuestionStatistics.objects.filter(question__survey=survey)
        .select_related("question")
        .order_by("question__order")
    ]
    return SurveyBreakdown(
        survey=survey,
        statistics=SurveyStatistics.objects.filter(survey=survey).first(),
        questions=questions,
    )


def _options_by_question(survey: Survey) -> dict[UUID, list[OptionBreakdown]]:
    grouped: dict[UUID, list[OptionBreakdown]] = {}
    rows = (
        OptionStatistics.objects.filter(option__question__survey=survey)
        .select_related("option")
        .order_by("option__question__order", "option__order")
    )
    for row in rows:
        grouped.setdefault(row.option.question_id, []).append(
            OptionBreakdown(
                id=row.option_id,
                text=row.option.text,
                order=row.option.order,
                selected_count=row.selected_count,
                updated_at=row.updated_at,
            )
        )
    return grouped
