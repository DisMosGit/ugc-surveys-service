from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from rest_framework.test import APITestCase

from accounts.enums import UserRole
from accounts.models import ApiUser
from surveys.enums import QuestionKind
from surveys.models import AnswerOption, Question, Survey

SURVEYS_URL = "/api/v1/surveys/"


class SurveyTestDataMixin:
    @property
    def author(self) -> ApiUser:
        cached: ApiUser | None = getattr(self, "_author", None)
        if cached is None:
            cached = ApiUser.objects.create(unsafe_id=1, role=UserRole.AUTHOR)
            self._author = cached
        return cached

    def create_survey(self) -> Survey:
        return Survey.objects.create(author=self.author, title="Овощи")


class SurveyModelTests(SurveyTestDataMixin, TestCase):
    def test_author_with_surveys_cannot_be_deleted(self) -> None:
        survey = self.create_survey()

        with self.assertRaises(ProtectedError):
            survey.author.delete()


class QuestionModelTests(SurveyTestDataMixin, TestCase):
    def test_question_order_is_unique_within_survey(self) -> None:
        survey = self.create_survey()
        Question.objects.create(survey=survey, text="Ты любишь огурцы?", order=1)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Question.objects.create(survey=survey, text="Ты любишь помидоры?", order=1)

        other = Question.objects.create(survey=self.create_survey(), text="Ты любишь огурцы?", order=1)

        self.assertEqual(other.order, 1)


class AnswerOptionModelTests(SurveyTestDataMixin, TestCase):
    def test_option_order_is_unique_within_question(self) -> None:
        question = Question.objects.create(survey=self.create_survey(), text="Ты любишь огурцы?", order=1)
        AnswerOption.objects.create(question=question, text="Да", order=1)
        AnswerOption.objects.create(question=question, text="Нет", order=2)
        AnswerOption.objects.create(question=question, text="Только в коктейлях", order=3)

        with self.assertRaises(IntegrityError), transaction.atomic():
            AnswerOption.objects.create(question=question, text="Только в коктейлях", order=1)


class AuthoringScenarioTests(APITestCase):
    def setUp(self) -> None:
        self.author = ApiUser.objects.create(unsafe_id=1, role=UserRole.AUTHOR)
        self.other_author = ApiUser.objects.create(unsafe_id=2, role=UserRole.AUTHOR)
        self.taker = ApiUser.objects.create(unsafe_id=3)

    def as_user(self, user: ApiUser) -> Any:
        return {"HTTP_X_UNSAFE_USER_ID": str(user.unsafe_id)}

    def route(self, *parts: str) -> str:
        return SURVEYS_URL + "".join(f"{part}/" for part in parts)

    def create_survey(self) -> str:
        response = self.client.post(
            SURVEYS_URL,
            {"title": "Овощи", "description": "Пример из задания"},
            format="json",
            **self.as_user(self.author),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["questions_count"], 0)
        return str(response.data["id"])

    def create_question(self, survey_id: str, **payload: Any) -> str:
        response = self.client.post(
            self.route(survey_id, "questions"), payload, format="json", **self.as_user(self.author)
        )
        self.assertEqual(response.status_code, 201)
        return str(response.data["id"])

    def create_option(self, question_id: str, text: str) -> str:
        response = self.client.post(
            f"/api/v1/questions/{question_id}/options/",
            {"text": text},
            format="json",
            **self.as_user(self.author),
        )
        self.assertEqual(response.status_code, 201)
        return str(response.data["id"])

    def questions(self, survey_id: str, user: ApiUser) -> list[dict[str, Any]]:
        response = self.client.get(self.route(survey_id, "questions"), **self.as_user(user))
        self.assertEqual(response.status_code, 200)
        return [dict(question) for question in response.data]

    def reorder(self, url: str, ids: list[str]) -> Any:
        return self.client.post(url, {"order": ids}, format="json", **self.as_user(self.author))

    def test_the_author_builds_the_survey_and_orders_it(self) -> None:
        self.assertEqual(self.client.post(SURVEYS_URL, {"title": "Овощи"}, format="json").status_code, 401)
        self.assertEqual(
            self.client.post(
                SURVEYS_URL, {"title": "Овощи"}, format="json", **self.as_user(self.taker)
            ).status_code,
            403,
        )

        survey_id = self.create_survey()
        cucumbers = self.create_question(survey_id, text="Ты любишь огурцы?")
        tomatoes = self.create_question(survey_id, text="Ты любишь помидоры?")
        free_form = self.create_question(survey_id, text="Что ещё добавить в салат?", kind=QuestionKind.TEXT)
        self.assertEqual(
            self.client.post(
                self.route(survey_id, "questions"),
                {"text": "Свой вопрос", "kind": QuestionKind.TEXT, "allows_custom_answer": False},
                format="json",
                **self.as_user(self.author),
            ).status_code,
            400,
        )

        option_ids = [self.create_option(cucumbers, text) for text in ("Да", "Нет", "Только в коктейлях")]
        tomatoes_yes = self.create_option(tomatoes, "Да")
        self.create_option(tomatoes, "Нет")

        questions = self.questions(survey_id, self.author)
        self.assertEqual(
            [(question["text"], question["order"]) for question in questions],
            [
                ("Ты любишь огурцы?", 1),
                ("Ты любишь помидоры?", 2),
                ("Что ещё добавить в салат?", 3),
            ],
        )
        self.assertEqual(
            [option["text"] for option in questions[0]["options"]],
            ["Да", "Нет", "Только в коктейлях"],
        )
        self.assertEqual([option["order"] for option in questions[0]["options"]], [1, 2, 3])
        self.assertEqual(
            [(question["kind"], question["allows_custom_answer"]) for question in questions],
            [
                (QuestionKind.SINGLE_CHOICE, True),
                (QuestionKind.SINGLE_CHOICE, True),
                (QuestionKind.TEXT, True),
            ],
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/questions/{free_form}/options/",
                {"text": "Да"},
                format="json",
                **self.as_user(self.author),
            ).status_code,
            400,
        )

        updated = self.client.patch(
            f"/api/v1/questions/{cucumbers}/",
            {"text": "Ты любишь огурцы? Уточните"},
            format="json",
            **self.as_user(self.author),
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["text"], "Ты любишь огурцы? Уточните")
        self.assertEqual(
            self.client.get(
                self.route(survey_id, "questions"), **self.as_user(self.other_author)
            ).status_code,
            404,
        )

        self.assertEqual(
            self.reorder(
                f"/api/v1/questions/{cucumbers}/options/reorder/", [option_ids[2], option_ids[0]]
            ).status_code,
            400,
        )

        reordered_options = self.reorder(
            f"/api/v1/questions/{cucumbers}/options/reorder/", [option_ids[2], option_ids[0], option_ids[1]]
        )
        self.assertEqual(reordered_options.status_code, 200)
        self.assertEqual(
            [(option["text"], option["order"]) for option in reordered_options.data],
            [("Только в коктейлях", 1), ("Да", 2), ("Нет", 3)],
        )

        reordered_questions = self.reorder(
            self.route(survey_id, "questions/reorder"), [tomatoes, cucumbers, free_form]
        )
        self.assertEqual(reordered_questions.status_code, 200)
        self.assertEqual(
            [(question["text"], question["order"]) for question in reordered_questions.data],
            [
                ("Ты любишь помидоры?", 1),
                ("Ты любишь огурцы? Уточните", 2),
                ("Что ещё добавить в салат?", 3),
            ],
        )

        self.assertEqual(
            self.client.post(
                self.route(survey_id, "answers"),
                {"question": tomatoes, "option": tomatoes_yes},
                format="json",
                **self.as_user(self.taker),
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.delete(self.route(survey_id), **self.as_user(self.author)).status_code, 409
        )
