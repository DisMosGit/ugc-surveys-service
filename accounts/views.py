from typing import Any

from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.models import ApiUser
from accounts.permissions import api_user
from accounts.serializers import ApiUserSerializer


class MeView(GenericAPIView[ApiUser]):
    serializer_class = ApiUserSerializer

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(api_user(request))
        return Response(serializer.data)
