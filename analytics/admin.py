from django.contrib import admin

from analytics.models import OptionStatistics, QuestionStatistics, SurveyStatistics


@admin.register(SurveyStatistics)
class SurveyStatisticsAdmin(admin.ModelAdmin):
    list_display = (
        "survey",
        "completed_count",
        "answers_count",
        "duration_sum_ms",
        "updated_at",
    )
    search_fields = ("survey__title",)
    autocomplete_fields = ("survey",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(QuestionStatistics)
class QuestionStatisticsAdmin(admin.ModelAdmin):
    list_display = ("question", "answers_count", "updated_at")
    search_fields = ("question__text",)
    autocomplete_fields = ("question",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(OptionStatistics)
class OptionStatisticsAdmin(admin.ModelAdmin):
    list_display = ("option", "selected_count", "updated_at")
    search_fields = ("option__text",)
    autocomplete_fields = ("option",)
    readonly_fields = ("id", "created_at", "updated_at")
