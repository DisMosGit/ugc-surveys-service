from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.enums import UserRole
from accounts.models import ApiUser
from analytics.models import OptionStatistics, QuestionStatistics, SurveyStatistics
from surveys.models import AnswerOption, Question, Survey


class StatisticsModelTests(TestCase):
    def setUp(self) -> None:
        author = ApiUser.objects.create(unsafe_id=1, role=UserRole.AUTHOR)
        self.survey = Survey.objects.create(author=author, title="Овощи")
        self.question = Question.objects.create(survey=self.survey, text="Ты любишь огурцы?", order=1)
        self.option = AnswerOption.objects.create(question=self.question, text="Да", order=1)

    def test_statistics_are_unique_per_subject(self) -> None:
        SurveyStatistics.objects.create(survey=self.survey)
        QuestionStatistics.objects.create(question=self.question)
        OptionStatistics.objects.create(option=self.option)

        with self.assertRaises(IntegrityError), transaction.atomic():
            SurveyStatistics.objects.create(survey=self.survey)

        with self.assertRaises(IntegrityError), transaction.atomic():
            QuestionStatistics.objects.create(question=self.question)

        with self.assertRaises(IntegrityError), transaction.atomic():
            OptionStatistics.objects.create(option=self.option)
