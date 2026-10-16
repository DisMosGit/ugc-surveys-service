from collections.abc import Sequence
from typing import Any

from django.db.models import QuerySet
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.permissions import IsAuthor, api_user
from surveys import selectors, services
from surveys.models import AnswerOption, Question, Survey
from surveys.serializers import (
    AnswerOptionSerializer,
    QuestionSerializer,
    ReorderSerializer,
    SurveySerializer,
)

AUTHOR_ACTIONS = {"create", "mine", "update", "partial_update", "destroy", "questions", "reorder_questions"}
OWN_ACTIONS = {"mine", "update", "partial_update", "destroy", "questions", "reorder_questions"}


class SurveyViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet[Survey],
):
    serializer_class = SurveySerializer

    def get_permissions(self) -> Sequence[BasePermission]:
        if self.action in AUTHOR_ACTIONS:
            return [IsAuthor()]
        return [IsAuthenticated()]

    def get_queryset(self) -> QuerySet[Survey]:
        user = api_user(self.request)
        if self.action == "list":
            return selectors.catalogue_surveys(user)
        if self.action in OWN_ACTIONS:
            return selectors.own_surveys(user)
        return selectors.visible_surveys(user)

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        survey = services.create_survey(author=api_user(request), data=serializer.validated_data)
        return Response(self.get_serializer(self._reload(survey)).data, status=status.HTTP_201_CREATED)

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=bool(kwargs.get("partial")))
        serializer.is_valid(raise_exception=True)
        survey = services.update_survey(instance, serializer.validated_data)
        return Response(self.get_serializer(self._reload(survey)).data)

    def perform_destroy(self, instance: Survey) -> None:
        services.delete_survey(instance)

    @action(detail=False, methods=["get"], url_path="mine")
    def mine(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return self.list(request, *args, **kwargs)

    @action(detail=True, methods=["get", "post"], url_path="questions")
    def questions(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        survey = self.get_object()
        if request.method == "POST":
            serializer = QuestionSerializer(data=request.data, context=self.get_serializer_context())
            serializer.is_valid(raise_exception=True)
            question = services.create_question(survey, serializer.validated_data)
            return Response(QuestionSerializer(question).data, status=status.HTTP_201_CREATED)
        return Response(QuestionSerializer(selectors.question_tree(survey), many=True).data)

    @action(detail=True, methods=["post"], url_path="questions/reorder")
    def reorder_questions(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        survey = self.get_object()
        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        questions = services.reorder_questions(survey, serializer.validated_data["order"])
        return Response(QuestionSerializer(questions, many=True).data)

    def _reload(self, survey: Survey) -> Survey:
        return self.get_queryset().get(pk=survey.pk)


class QuestionViewSet(
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet[Question],
):
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthor]

    def get_queryset(self) -> QuerySet[Question]:
        return selectors.owned_questions(api_user(self.request))

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=bool(kwargs.get("partial")))
        serializer.is_valid(raise_exception=True)
        question = services.update_question(instance, serializer.validated_data)
        return Response(self.get_serializer(self.get_queryset().get(pk=question.pk)).data)

    def perform_destroy(self, instance: Question) -> None:
        services.delete_question(instance)

    @action(detail=True, methods=["get", "post"], url_path="options")
    def answer_options(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        question = self.get_object()
        if request.method == "POST":
            serializer = AnswerOptionSerializer(data=request.data, context=self.get_serializer_context())
            serializer.is_valid(raise_exception=True)
            option = services.create_option(question, serializer.validated_data)
            return Response(AnswerOptionSerializer(option).data, status=status.HTTP_201_CREATED)
        return Response(AnswerOptionSerializer(selectors.option_tree(question), many=True).data)

    @action(detail=True, methods=["post"], url_path="options/reorder")
    def reorder_options(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        question = self.get_object()
        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        options = services.reorder_options(question, serializer.validated_data["order"])
        return Response(AnswerOptionSerializer(options, many=True).data)


class AnswerOptionViewSet(
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet[AnswerOption],
):
    serializer_class = AnswerOptionSerializer
    permission_classes = [IsAuthor]

    def get_queryset(self) -> QuerySet[AnswerOption]:
        return selectors.owned_options(api_user(self.request))

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=bool(kwargs.get("partial")))
        serializer.is_valid(raise_exception=True)
        option = services.update_option(instance, serializer.validated_data)
        return Response(self.get_serializer(self.get_queryset().get(pk=option.pk)).data)

    def perform_destroy(self, instance: AnswerOption) -> None:
        services.delete_option(instance)
