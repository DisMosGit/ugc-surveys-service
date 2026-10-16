from django.conf import settings
from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path, re_path
from django.views.static import serve
from rest_framework.routers import DefaultRouter

from accounts.views import MeView
from analytics.views import SurveyStatisticsViewSet
from answers.views import NextQuestionViewSet, SessionStartViewSet, SubmitAnswerViewSet
from surveys.views import AnswerOptionViewSet, QuestionViewSet, SurveyViewSet

router = DefaultRouter()
router.register("surveys", NextQuestionViewSet, basename="next-question")
router.register("surveys", SessionStartViewSet, basename="survey-session")
router.register("surveys", SubmitAnswerViewSet, basename="survey-answer")
router.register("surveys", SurveyStatisticsViewSet, basename="survey-statistics")
router.register("surveys", SurveyViewSet, basename="survey")
router.register("questions", QuestionViewSet, basename="question")
router.register("answer-options", AnswerOptionViewSet, basename="answer-option")

api_patterns: list[URLPattern | URLResolver] = [
    path("me/", MeView.as_view(), name="me"),
    *router.urls,
]

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_patterns)),
]

if settings.SERVE_MEDIA:
    urlpatterns.append(re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}))
