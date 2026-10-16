from typing import Any

from rest_framework import serializers

from answers.models import SurveySession
from surveys.enums import QuestionKind
from surveys.models import AnswerOption, Question, Survey


class SurveySessionProgressSerializer(serializers.ModelSerializer[SurveySession]):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = SurveySession
        fields = ["status", "status_display", "answered_count"]
        read_only_fields = ["status", "status_display", "answered_count"]


class SessionProgressSerializer(serializers.Serializer[Any]):
    session = serializers.UUIDField()
    survey = serializers.UUIDField()
    status = serializers.IntegerField()
    status_display = serializers.CharField()
    answered_count = serializers.IntegerField()
    questions_count = serializers.IntegerField()


class SurveyOptionSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    text = serializers.CharField()
    order = serializers.IntegerField()


class QuestionInSurveySerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    text = serializers.CharField()
    order = serializers.IntegerField()
    kind = serializers.IntegerField()
    kind_display = serializers.CharField(source="get_kind_display")
    allows_custom_answer = serializers.BooleanField()
    is_required = serializers.BooleanField()
    options = SurveyOptionSerializer(source="active_options", many=True)


class NextQuestionSerializer(SessionProgressSerializer):
    question = QuestionInSurveySerializer()


class AnswerSubmitSerializer(serializers.Serializer[Any]):
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    option = serializers.PrimaryKeyRelatedField(
        queryset=AnswerOption.objects.all(), required=False, allow_null=True
    )
    custom_text = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True, default="")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        survey: Survey = self.context["survey"]
        question: Question = attrs["question"]
        option: AnswerOption | None = attrs.get("option")
        custom_text: str = attrs["custom_text"]

        if question.survey_id != survey.pk:
            raise serializers.ValidationError({"question": "Вопрос не относится к этому опросу"})
        if option is not None:
            if option.question_id != question.pk:
                raise serializers.ValidationError({"option": "Вариант ответа не относится к этому вопросу"})
            if not option.is_active:
                raise serializers.ValidationError({"option": "Вариант ответа отключён"})
        if question.kind == QuestionKind.TEXT:
            if option is not None:
                raise serializers.ValidationError(
                    {"option": "Для вопроса со свободным ответом вариант не выбирается"}
                )
            if not custom_text:
                raise serializers.ValidationError({"custom_text": "Укажите свой вариант ответа"})
            return attrs
        if option is None and not custom_text:
            raise serializers.ValidationError("Укажите вариант ответа или свой текст")
        if option is not None and custom_text:
            raise serializers.ValidationError("Выберите вариант ответа или укажите текст, но не оба сразу")
        if custom_text and not question.allows_custom_answer:
            raise serializers.ValidationError(
                {"custom_text": "Для этого вопроса свой вариант ответа запрещён"}
            )
        return attrs


def session_payload(session: SurveySession, questions_count: int) -> dict[str, Any]:
    return {
        "session": session.pk,
        "survey": session.survey_id,
        "status": session.status,
        "status_display": session.get_status_display(),
        "answered_count": session.answered_count,
        "questions_count": questions_count,
    }
