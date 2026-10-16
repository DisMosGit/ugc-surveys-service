from typing import Any

from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.permissions import IsAuthor, api_user
from analytics import selectors
from analytics.serializers import SurveyStatisticsSerializer
from surveys.models import Survey


class SurveyStatisticsViewSet(viewsets.GenericViewSet[Any]):
    serializer_class = SurveyStatisticsSerializer
    permission_classes = [IsAuthor]
    lookup_url_kwarg = "survey_id"

    def get_queryset(self) -> QuerySet[Survey]:
        return Survey.objects.filter(author=api_user(self.request))

    @action(detail=True, methods=["get"], url_path="statistics", url_name="detail")
    def statistics(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return Response(self.get_serializer(selectors.survey_breakdown(self.get_object())).data)
