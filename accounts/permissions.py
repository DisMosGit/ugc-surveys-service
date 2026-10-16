from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from accounts.enums import UserRole
from accounts.models import ApiUser


def api_user(request: Request) -> ApiUser:
    user = request.user
    if not isinstance(user, ApiUser):
        raise NotAuthenticated("Пользователь не идентифицирован")
    return user


class IsAuthor(BasePermission):
    message = "Действие доступно только авторам опросов"

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return isinstance(user, ApiUser) and user.role == UserRole.AUTHOR
