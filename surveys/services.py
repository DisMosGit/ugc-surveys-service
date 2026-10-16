from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Field, Max, ProtectedError
from django.utils import timezone

from accounts.models import ApiUser
from core.exceptions import EntityInUse, InvalidOrdering, OptionsNotAllowed
from surveys.enums import QuestionKind
from surveys.models import AnswerOption, Question, Survey

ORDER_OFFSET = 1000


def create_survey(author: ApiUser, data: Mapping[str, Any]) -> Survey:
    return Survey.objects.create(author=author, **data)


def update_survey(survey: Survey, data: Mapping[str, Any]) -> Survey:
    for field, value in data.items():
        setattr(survey, field, value)
    survey.save()
    return survey


def delete_survey(survey: Survey) -> None:
    try:
        with transaction.atomic():
            survey.delete()
    except ProtectedError:
        raise EntityInUse("Опрос нельзя удалить: по нему уже есть ответы. Деактивируйте его") from None


def create_question(survey: Survey, data: Mapping[str, Any]) -> Question:
    with transaction.atomic():
        _bump_version(survey.pk)
        question = Question.objects.create(survey=survey, order=_next_question_order(survey), **data)
    return question


def update_question(question: Question, data: Mapping[str, Any]) -> Question:
    with transaction.atomic():
        _bump_version(question.survey_id)
        current_kind = _current_kind(question)
        if data.get("kind") == QuestionKind.TEXT and current_kind != QuestionKind.TEXT:
            if _has_options(question):
                raise OptionsNotAllowed("У вопроса уже есть варианты ответа: сначала удалите их")
        for field, value in data.items():
            setattr(question, field, value)
        question.save()
    return question


def delete_question(question: Question) -> None:
    survey_id = question.survey_id
    try:
        with transaction.atomic():
            _bump_version(survey_id)
            question.delete()
            _renumber_questions(survey_id)
    except ProtectedError:
        raise EntityInUse("Вопрос нельзя удалить: на него уже есть ответы") from None


def create_option(question: Question, data: Mapping[str, Any]) -> AnswerOption:
    with transaction.atomic():
        _bump_version(question.survey_id)
        if _current_kind(question) == QuestionKind.TEXT:
            raise OptionsNotAllowed()
        option = AnswerOption.objects.create(question=question, order=_next_option_order(question), **data)
    return option


def update_option(option: AnswerOption, data: Mapping[str, Any]) -> AnswerOption:
    with transaction.atomic():
        _bump_version(option.question.survey_id)
        for field, value in data.items():
            setattr(option, field, value)
        option.save()
    return option


def delete_option(option: AnswerOption) -> None:
    question = option.question
    try:
        with transaction.atomic():
            _bump_version(question.survey_id)
            option.delete()
            _renumber_options(question)
    except ProtectedError:
        raise EntityInUse("Вариант ответа нельзя удалить: его уже выбирали. Деактивируйте его") from None


def reorder_questions(survey: Survey, ids: Sequence[str]) -> list[Question]:
    with transaction.atomic():
        _bump_version(survey.pk)
        questions = _ordered_questions(survey, ids)
        Question.objects.filter(survey=survey).update(
            order=F("order") + ORDER_OFFSET, updated_at=timezone.now()
        )
        for order, question in enumerate(questions, start=1):
            question.order = order
            question.save(update_fields=["order"])
    return questions


def reorder_options(question: Question, ids: Sequence[str]) -> list[AnswerOption]:
    with transaction.atomic():
        _bump_version(question.survey_id)
        options = _ordered_options(question, ids)
        AnswerOption.objects.filter(question=question).update(
            order=F("order") + ORDER_OFFSET, updated_at=timezone.now()
        )
        for order, option in enumerate(options, start=1):
            option.order = order
            option.save(update_fields=["order"])
    return options


def _next_question_order(survey: Survey) -> int:
    maximum = Question.objects.filter(survey=survey).aggregate(value=Max("order"))["value"]
    return 1 if maximum is None else int(maximum) + 1


def _next_option_order(question: Question) -> int:
    maximum = AnswerOption.objects.filter(question=question).aggregate(value=Max("order"))["value"]
    return 1 if maximum is None else int(maximum) + 1


def _renumber_questions(survey_id: UUID) -> None:
    questions = Question.objects.filter(survey_id=survey_id).order_by("order")
    for order, question in enumerate(questions, start=1):
        if question.order != order:
            question.order = order
            question.save(update_fields=["order"])


def _renumber_options(question: Question) -> None:
    options = AnswerOption.objects.filter(question=question).order_by("order")
    for order, option in enumerate(options, start=1):
        if option.order != order:
            option.order = order
            option.save(update_fields=["order"])


def _bump_version(survey_id: UUID) -> None:
    Survey.objects.filter(pk=survey_id).update(version=F("version") + 1, updated_at=timezone.now())


def _current_kind(question: Question) -> int:
    return int(Question.objects.values_list("kind", flat=True).get(pk=question.pk))


def _has_options(question: Question) -> bool:
    return AnswerOption.objects.filter(question=question).exists()


def _normalize_id(pk_field: Field[Any, Any], raw: str) -> UUID:
    try:
        value = pk_field.to_python(raw)
    except ValidationError, ValueError, TypeError:
        raise InvalidOrdering("Некорректный идентификатор в порядке") from None
    if not isinstance(value, UUID):
        raise InvalidOrdering("Некорректный идентификатор в порядке")
    return value


def _ordered_questions(survey: Survey, ids: Sequence[str]) -> list[Question]:
    positions = [_normalize_id(Question._meta.pk, raw) for raw in ids]
    questions = {question.pk: question for question in Question.objects.filter(survey=survey)}
    if len(positions) != len(set(positions)) or set(positions) != set(questions):
        raise InvalidOrdering("Порядок должен содержать все вопросы опроса без пропусков и повторов")
    return [questions[position] for position in positions]


def _ordered_options(question: Question, ids: Sequence[str]) -> list[AnswerOption]:
    positions = [_normalize_id(AnswerOption._meta.pk, raw) for raw in ids]
    options = {option.pk: option for option in AnswerOption.objects.filter(question=question)}
    if len(positions) != len(set(positions)) or set(positions) != set(options):
        raise InvalidOrdering("Порядок должен содержать все варианты ответа без пропусков и повторов")
    return [options[position] for position in positions]
