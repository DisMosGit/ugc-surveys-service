from typing import Any

from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

from accounts.enums import UserRole
from accounts.models import ApiUser
from answers.enums import SessionStatus
from answers.models import Answer, SurveySession
from surveys.enums import QuestionKind
from surveys.models import AnswerOption, Question, Survey

HEADER = "HTTP_X_UNSAFE_USER_ID"

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


class TakingScenarioTests(AnswerTestDataMixin, APITestCase):
    def setUp(self) -> None:
        self.survey = self.create_example_survey()
        self.first, self.second = Question.objects.filter(survey=self.survey).order_by("order")
        self.first_options = list(AnswerOption.objects.filter(question=self.first).order_by("order"))
        self.second_options = list(AnswerOption.objects.filter(question=self.second).order_by("order"))
        self.free_form = Question.objects.create(
            survey=self.survey, text="Что ещё добавить?", order=3, kind=QuestionKind.TEXT
        )
        self.second.allows_custom_answer = False
        self.second.save(update_fields=["allows_custom_answer"])

    def as_user(self, unsafe_id: int) -> dict[str, Any]:
        return {HEADER: str(unsafe_id)}

    def url(self, action: str) -> str:
        return f"/api/v1/surveys/{self.survey.pk}/{action}/"

    def next_question(self, unsafe_id: int) -> Any:
        return self.client.get(self.url("next-question"), **self.as_user(unsafe_id))

    def answer(self, unsafe_id: int, payload: dict[str, Any]) -> Any:
        return self.client.post(self.url("answers"), payload, format="json", **self.as_user(unsafe_id))

    def statistics(self, unsafe_id: int) -> Any:
        return self.client.get(self.url("statistics"), **self.as_user(unsafe_id))

    def test_the_user_passes_the_survey_question_by_question(self) -> None:
        started = self.next_question(2)

        self.assertEqual(started.status_code, 200)
        self.assertEqual(started.data["answered_count"], 0)
        self.assertEqual(started.data["questions_count"], 3)
        self.assertEqual(started.data["question"]["text"], "Ты любишь огурцы?")
        self.assertEqual(
            [option["text"] for option in started.data["question"]["options"]],
            ["Да", "Нет", "Только в коктейлях"],
        )

        answered = self.answer(2, {"question": str(self.first.pk), "option": str(self.first_options[2].pk)})

        self.assertEqual(answered.status_code, 200)
        self.assertEqual(
            (answered.data["answered_count"], answered.data["status"]), (1, SessionStatus.ACTIVE)
        )
        self.assertEqual(self.next_question(2).data["question"]["text"], "Ты любишь помидоры?")

        custom = self.answer(2, {"question": str(self.first.pk), "custom_text": "  В салате  "})
        session = SurveySession.objects.get(pk=started.data["session"])

        self.assertEqual(custom.status_code, 200)
        self.assertEqual(custom.data["answered_count"], 1)
        self.assertEqual(Answer.objects.filter(session=session).count(), 1)
        self.assertEqual(Answer.objects.get(session=session, question=self.first).custom_text, "В салате")

        self.assertEqual(
            self.answer(2, {"question": str(self.second.pk), "custom_text": "Не знаю"}).status_code, 400
        )
        self.assertEqual(
            self.answer(
                2, {"question": str(self.free_form.pk), "option": str(self.first_options[0].pk)}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.answer(2, {"question": str(self.free_form.pk), "custom_text": ""}).status_code, 400
        )

        finished = self.answer(2, {"question": str(self.second.pk), "option": str(self.second_options[0].pk)})

        self.assertEqual(finished.data["answered_count"], 2)
        self.assertEqual(finished.data["status"], SessionStatus.ACTIVE)

        completed = self.answer(2, {"question": str(self.free_form.pk), "custom_text": "Оливки"})
        session.refresh_from_db()

        self.assertEqual(completed.data["answered_count"], 3)
        self.assertEqual(completed.data["status"], SessionStatus.COMPLETED)
        self.assertEqual((session.status, session.answered_count), (SessionStatus.COMPLETED, 3))
        self.assertIsNotNone(session.completed_at)
        self.assertEqual(self.next_question(2).status_code, 204)
        self.assertEqual(
            self.answer(
                2, {"question": str(self.first.pk), "option": str(self.first_options[0].pk)}
            ).status_code,
            409,
        )

        restarted = self.client.post(self.url("sessions"), **self.as_user(2))

        self.assertEqual(restarted.status_code, 201)
        self.assertEqual(restarted.data["answered_count"], 0)
        self.assertEqual(self.next_question(2).data["question"]["text"], "Ты любишь огурцы?")
        self.assertEqual(self.next_question(3).data["answered_count"], 0)
        self.assertEqual(Answer.objects.filter(session=session).count(), 3)

    def test_the_author_reads_the_statistics_of_the_assignment(self) -> None:
        self.answer(2, {"question": str(self.first.pk), "option": str(self.first_options[2].pk)})
        self.answer(2, {"question": str(self.second.pk), "option": str(self.second_options[0].pk)})
        self.answer(2, {"question": str(self.free_form.pk), "custom_text": "Оливки"})
        self.answer(3, {"question": str(self.first.pk), "custom_text": "В салате"})

        self.assertEqual(self.statistics(2).status_code, 403)
        response = self.statistics(1)

        self.assertEqual(response.status_code, 200)
        counters = response.data["statistics"]
        self.assertEqual((counters["answers_count"], counters["completed_count"]), (4, 1))
        self.assertGreaterEqual(counters["duration_sum_ms"], 0)
        self.assertEqual(counters["average_duration_ms"], counters["duration_sum_ms"])

        questions = response.data["questions"]

        self.assertEqual(
            [question["text"] for question in questions],
            ["Ты любишь огурцы?", "Ты любишь помидоры?", "Что ещё добавить?"],
        )
        self.assertEqual([question["answers_count"] for question in questions], [2, 1, 1])
        self.assertEqual(
            [(option["text"], option["selected_count"]) for option in questions[0]["options"]],
            [("Только в коктейлях", 1)],
        )
        self.assertEqual(
            [(option["text"], option["selected_count"]) for option in questions[1]["options"]],
            [("Да", 1)],
        )
        self.assertEqual(questions[2]["options"], [])
