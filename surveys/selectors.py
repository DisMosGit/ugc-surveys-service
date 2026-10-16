from django.db.models import Count, Prefetch, Q, QuerySet

from accounts.models import ApiUser
from answers.models import SurveySession
from surveys.models import AnswerOption, Question, Survey


def _with_user_sessions(queryset: QuerySet[Survey], user: ApiUser) -> QuerySet[Survey]:
    sessions = SurveySession.objects.filter(user=user).order_by("-created_at")
    return (
        queryset.annotate(questions_count=Count("questions"))
        .order_by("-created_at")
        .prefetch_related(Prefetch("sessions", queryset=sessions, to_attr="user_sessions"))
    )


def catalogue_surveys(user: ApiUser) -> QuerySet[Survey]:
    return _with_user_sessions(Survey.objects.filter(is_active=True), user)


def visible_surveys(user: ApiUser) -> QuerySet[Survey]:
    return _with_user_sessions(Survey.objects.filter(Q(is_active=True) | Q(author=user)), user)


def own_surveys(user: ApiUser) -> QuerySet[Survey]:
    return _with_user_sessions(Survey.objects.filter(author=user), user)


def owned_questions(user: ApiUser) -> QuerySet[Question]:
    return Question.objects.filter(survey__author=user)


def owned_options(user: ApiUser) -> QuerySet[AnswerOption]:
    return AnswerOption.objects.filter(question__survey__author=user)


def question_tree(survey: Survey) -> QuerySet[Question]:
    return Question.objects.filter(survey=survey).prefetch_related("options")


def option_tree(question: Question) -> QuerySet[AnswerOption]:
    return AnswerOption.objects.filter(question=question)
