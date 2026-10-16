from django.contrib import admin

from answers.models import Answer, SurveySession


@admin.register(SurveySession)
class SurveySessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "survey",
        "user",
        "status",
        "answered_count",
        "created_at",
        "completed_at",
    )
    list_filter = ("status",)
    search_fields = ("user__unsafe_id", "survey__title")
    autocomplete_fields = ("survey", "user")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "question", "option", "created_at")
    search_fields = ("question__text", "custom_text")
    autocomplete_fields = ("session", "question", "option")
    readonly_fields = ("id", "created_at", "updated_at")
