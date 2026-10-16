from django.db import transaction
from django.utils import timezone

from accounts.models import ApiUser
from answers import selectors
from answers.enums import SessionStatus
from answers.models import Answer, SurveySession
from core.exceptions import SessionCompleted
from surveys.models import AnswerOption, Question, Survey


def start_or_resume_session(user: ApiUser, survey: Survey) -> tuple[SurveySession, bool]:
    session, created = SurveySession.objects.get_or_create(
        user=user,
        survey=survey,
        status=SessionStatus.ACTIVE,
        defaults={"survey_version": survey.version},
    )
    return session, created


def open_session(user: ApiUser, survey: Survey) -> SurveySession | None:
    session = selectors.active_session(user, survey)
    if session is not None:
        return session
    if selectors.has_sessions(user, survey):
        return None
    return start_or_resume_session(user, survey)[0]


def next_question(session: SurveySession) -> Question | None:
    question = selectors.unanswered_question(session)
    if question is None and session.status == SessionStatus.ACTIVE:
        session.status = SessionStatus.COMPLETED
        session.completed_at = timezone.now()
        session.save(update_fields=["status", "completed_at", "updated_at"])
    return question


def submit_answer(
    session: SurveySession,
    *,
    question: Question,
    option: AnswerOption | None,
    custom_text: str,
) -> SurveySession:
    with transaction.atomic():
        existing = Answer.objects.filter(session=session, question=question).first()
        if session.status == SessionStatus.COMPLETED and existing is None:
            raise SessionCompleted("Прохождение завершено, начните новое")
        _, created = Answer.objects.update_or_create(
            session=session,
            question=question,
            defaults={"option": option, "custom_text": custom_text},
        )
        if created:
            session.answered_count += 1
            session.last_answered_order = max(session.last_answered_order, question.order)
        has_unanswered = (
            Question.objects.filter(survey_id=session.survey_id).exclude(answers__session=session).exists()
        )
        session.status = SessionStatus.ACTIVE if has_unanswered else SessionStatus.COMPLETED
        session.completed_at = None if has_unanswered else session.completed_at or timezone.now()
        session.save(
            update_fields=[
                "answered_count",
                "last_answered_order",
                "status",
                "completed_at",
                "updated_at",
            ]
        )
    return session
