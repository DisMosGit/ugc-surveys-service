from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from accounts.enums import UserRole
from accounts.models import ApiUser
from surveys.models import AnswerOption, Question, Survey


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
