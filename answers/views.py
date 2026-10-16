from typing import Any

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.permissions import api_user
from answers import selectors, services
from answers.serializers import (
    AnswerSubmitSerializer,
    NextQuestionSerializer,
    SessionProgressSerializer,
    session_payload,
)
from core.exceptions import SessionCompleted
from surveys.models import Survey


class SurveyScopedViewSet(viewsets.GenericViewSet[Any]):
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "survey_id"
    survey: Survey

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)
        self.survey = get_object_or_404(Survey.objects.filter(is_active=True), pk=self.kwargs["survey_id"])

    def get_serializer_context(self) -> dict[str, Any]:
        return {**super().get_serializer_context(), "survey": self.survey}


class SessionStartViewSet(SurveyScopedViewSet):
    serializer_class = SessionProgressSerializer

    @action(detail=True, methods=["post"], url_path="sessions", url_name="detail")
    def start_session(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        session, created = services.start_or_resume_session(api_user(request), self.survey)
        payload = session_payload(session, selectors.question_count(self.survey))
        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(self.get_serializer(payload).data, status=code)


class NextQuestionViewSet(SurveyScopedViewSet):
    serializer_class = NextQuestionSerializer

    @action(detail=True, methods=["get"], url_path="next-question", url_name="detail")
    def next_question(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        session = services.open_session(api_user(request), self.survey)
        if session is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        question = services.next_question(session)
        if question is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        payload = {**session_payload(session, selectors.question_count(self.survey)), "question": question}
        return Response(self.get_serializer(payload).data)


class SubmitAnswerViewSet(SurveyScopedViewSet):
    serializer_class = AnswerSubmitSerializer

    @action(detail=True, methods=["post"], url_path="answers", url_name="detail")
    def submit_answer(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = services.open_session(api_user(request), self.survey)
        if session is None:
            raise SessionCompleted("Прохождение завершено, начните новое")
        validated = serializer.validated_data
        session = services.submit_answer(
            session,
            question=validated["question"],
            option=validated.get("option"),
            custom_text=validated["custom_text"],
        )
        payload = session_payload(session, selectors.question_count(self.survey))
        return Response(SessionProgressSerializer(payload).data)
