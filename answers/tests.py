from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.enums import UserRole
from accounts.models import ApiUser
from answers.enums import SessionStatus
from answers.models import Answer, SurveySession
from surveys.models import AnswerOption, Question, Survey

EXAMPLE_QUESTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Ты любишь огурцы?", ("Да", "Нет", "Только в коктейлях")),
    ("Ты любишь помидоры?", ("Да", "Нет", "Только если гаспаччо")),
)


class AnswerTestDataMixin:
    @property
    def author(self) -> ApiUser:
        cached: ApiUser | None = getattr(self, "_author", None)
        if cached is None:
            cached = ApiUser.objects.create(unsafe_id=1, role=UserRole.AUTHOR)
            self._author = cached
        return cached

    @staticmethod
    def create_user(unsafe_id: int = 2) -> ApiUser:
        user, _ = ApiUser.objects.get_or_create(unsafe_id=unsafe_id)
        return user

    def create_example_survey(self) -> Survey:
        survey = Survey.objects.create(author=self.author, title="Овощи")
        for order, (text, options) in enumerate(EXAMPLE_QUESTIONS, start=1):
            question = Question.objects.create(survey=survey, text=text, order=order)
            for option_order, option_text in enumerate(options, start=1):
                AnswerOption.objects.create(question=question, text=option_text, order=option_order)
        return survey


class SurveySessionModelTests(AnswerTestDataMixin, TestCase):
    def test_only_one_active_session_per_user_and_survey(self) -> None:
        survey = self.create_example_survey()
        user = self.create_user()
        first = SurveySession.objects.create(survey=survey, user=user)

        with self.assertRaises(IntegrityError), transaction.atomic():
            SurveySession.objects.create(survey=survey, user=user)

        another = SurveySession.objects.create(survey=survey, user=self.create_user(3))

        self.assertNotEqual(another.pk, first.pk)

        first.status = SessionStatus.COMPLETED
        first.save(update_fields=["status"])

        self.assertIsNotNone(SurveySession.objects.create(survey=survey, user=user).pk)

    def test_next_question_follows_the_order_cursor(self) -> None:
        survey = self.create_example_survey()
        first = Question.objects.get(survey=survey, order=1)
        second = Question.objects.get(survey=survey, order=2)
        session = SurveySession.objects.create(survey=survey, user=self.create_user())
        questions = Question.objects.filter(survey=survey).order_by("order")

        self.assertEqual(questions.filter(order__gt=session.last_answered_order).first(), first)

        session.last_answered_order = first.order
        session.answered_count = 1
        session.save(update_fields=["last_answered_order", "answered_count"])

        self.assertEqual(questions.filter(order__gt=session.last_answered_order).first(), second)

        session.last_answered_order = second.order
        session.answered_count = 2
        session.save(update_fields=["last_answered_order", "answered_count"])

        self.assertIsNone(questions.filter(order__gt=session.last_answered_order).first())


class AnswerModelTests(AnswerTestDataMixin, TestCase):
    def setUp(self) -> None:
        self.survey = self.create_example_survey()
        self.question = Question.objects.get(survey=self.survey, order=1)
        self.option = AnswerOption.objects.get(question=self.question, order=1)
        self.session = SurveySession.objects.create(survey=self.survey, user=self.create_user())

    def test_answer_accepts_option_or_custom_text(self) -> None:
        by_option = Answer.objects.create(session=self.session, question=self.question, option=self.option)

        self.assertEqual(by_option.option, self.option)
        self.assertEqual(by_option.custom_text, "")

        other = SurveySession.objects.create(survey=self.survey, user=self.create_user(3))
        by_text = Answer.objects.create(session=other, question=self.question, custom_text="Только в салате")

        self.assertIsNone(by_text.option)
        self.assertEqual(by_text.custom_text, "Только в салате")

    def test_answer_rejects_two_sources_or_none(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            Answer.objects.create(
                session=self.session,
                question=self.question,
                option=self.option,
                custom_text="Только в салате",
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Answer.objects.create(session=self.session, question=self.question)

    def test_one_answer_per_question_within_session(self) -> None:
        Answer.objects.create(session=self.session, question=self.question, option=self.option)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Answer.objects.create(session=self.session, question=self.question, custom_text="Только в салате")

        other = SurveySession.objects.create(survey=self.survey, user=self.create_user(3))
        repeated = Answer.objects.create(session=other, question=self.question, option=self.option)

        self.assertIsNotNone(repeated.pk)
