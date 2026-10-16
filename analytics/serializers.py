from typing import Any

from rest_framework import serializers

from analytics.models import SurveyStatistics


class SurveyIdentitySerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    title = serializers.CharField()


class SurveyCountersSerializer(serializers.Serializer[Any]):
    started_count = serializers.IntegerField()
    completed_count = serializers.IntegerField()
    abandoned_count = serializers.IntegerField()
    answers_count = serializers.IntegerField()
    duration_sum_ms = serializers.IntegerField()
    average_duration_ms = serializers.SerializerMethodField()
    updated_at = serializers.DateTimeField()

    def get_average_duration_ms(self, obj: SurveyStatistics) -> int | None:
        if not obj.completed_count:
            return None
        return obj.duration_sum_ms // obj.completed_count


class OptionStatisticsSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    text = serializers.CharField()
    order = serializers.IntegerField()
    selected_count = serializers.IntegerField()
    custom_answers_count = serializers.IntegerField()
    updated_at = serializers.DateTimeField()


class QuestionStatisticsSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    text = serializers.CharField()
    order = serializers.IntegerField()
    answers_count = serializers.IntegerField()
    skipped_count = serializers.IntegerField()
    updated_at = serializers.DateTimeField()
    options = OptionStatisticsSerializer(many=True)


class SurveyStatisticsSerializer(serializers.Serializer[Any]):
    survey = SurveyIdentitySerializer()
    statistics = SurveyCountersSerializer(allow_null=True)
    questions = QuestionStatisticsSerializer(many=True)
