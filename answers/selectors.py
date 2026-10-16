from django.db.models import Prefetch

from accounts.models import ApiUser
from answers.enums import SessionStatus
from answers.models import SurveySession
from surveys.models import AnswerOption, Question, Survey


def active_session(user: ApiUser, survey: Survey) -> SurveySession | None:
    return SurveySession.objects.filter(user=user, survey=survey, status=SessionStatus.ACTIVE).first()


def has_sessions(user: ApiUser, survey: Survey) -> bool:
    return SurveySession.objects.filter(user=user, survey=survey).exists()


def question_count(survey: Survey) -> int:
    return Question.objects.filter(survey=survey).count()


def unanswered_question(session: SurveySession) -> Question | None:
    options = AnswerOption.objects.filter(is_active=True)
    return (
        Question.objects.filter(survey_id=session.survey_id)
        .exclude(answers__session=session)
        .prefetch_related(Prefetch("options", queryset=options, to_attr="active_options"))
        .order_by("order")
        .first()
    )
