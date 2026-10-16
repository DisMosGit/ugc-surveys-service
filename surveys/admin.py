from django.contrib import admin

from surveys.models import AnswerOption, Question, Survey


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 0
    fields = ("order", "text", "is_active")
    ordering = ("order",)


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ("order", "text", "kind", "allows_custom_answer", "is_required")
    ordering = ("order",)
    show_change_link = True


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "is_active", "version", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title", "author__unsafe_id")
    autocomplete_fields = ("author",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = (QuestionInline,)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "survey", "order", "kind", "is_required")
    list_filter = ("kind", "is_required", "allows_custom_answer")
    search_fields = ("text", "survey__title")
    autocomplete_fields = ("survey",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = (AnswerOptionInline,)


@admin.register(AnswerOption)
class AnswerOptionAdmin(admin.ModelAdmin):
    list_display = ("text", "question", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("text", "question__text")
    autocomplete_fields = ("question",)
    readonly_fields = ("id", "created_at", "updated_at")
