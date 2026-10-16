from typing import Any

from rest_framework import serializers

from answers.models import SurveySession
from answers.serializers import SurveySessionProgressSerializer
from surveys.enums import QuestionKind
from surveys.models import AnswerOption, Question, Survey


class SurveySerializer(serializers.ModelSerializer[Survey]):
    questions_count = serializers.SerializerMethodField()
    session = serializers.SerializerMethodField()

    class Meta:
        model = Survey
        fields = [
            "id",
            "title",
            "description",
            "is_active",
            "version",
            "questions_count",
            "session",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "version", "questions_count", "session", "created_at", "updated_at"]

    def get_questions_count(self, obj: Survey) -> int:
        return int(getattr(obj, "questions_count", 0))

    def get_session(self, obj: Survey) -> dict[str, Any] | None:
        sessions: list[SurveySession] = getattr(obj, "user_sessions", [])
        if not sessions:
            return None
        return dict(SurveySessionProgressSerializer(sessions[0]).data)


class AnswerOptionSerializer(serializers.ModelSerializer[AnswerOption]):
    class Meta:
        model = AnswerOption
        fields = ["id", "text", "order", "is_active"]
        read_only_fields = ["id", "order"]


class QuestionSerializer(serializers.ModelSerializer[Question]):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    options = AnswerOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "text",
            "order",
            "kind",
            "kind_display",
            "allows_custom_answer",
            "is_required",
            "options",
        ]
        read_only_fields = ["id", "order", "kind_display", "options"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        instance = self.instance if isinstance(self.instance, Question) else None
        kind = attrs.get("kind", instance.kind if instance is not None else QuestionKind.SINGLE_CHOICE)
        allows_custom_answer = attrs.get(
            "allows_custom_answer",
            instance.allows_custom_answer if instance is not None else True,
        )
        if kind == QuestionKind.TEXT and not allows_custom_answer:
            raise serializers.ValidationError(
                {"allows_custom_answer": "Для вопроса со свободным ответом свой вариант обязателен"}
            )
        return attrs


class ReorderSerializer(serializers.Serializer[Any]):
    order = serializers.ListField(child=serializers.CharField(), allow_empty=True)
