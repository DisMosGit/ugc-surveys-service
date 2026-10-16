from dataclasses import dataclass
from typing import Any

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from accounts.models import MAX_UNSAFE_ID, MIN_UNSAFE_ID, ApiUser

DEFAULT_UNSAFE_USER_HEADER = "X-Unsafe-User-Id"


@dataclass(frozen=True)
class UnsafeUserToken:
    unsafe_id: int


class UnsafeUserAuthentication(BaseAuthentication):
    def authenticate(self, request: Any) -> tuple[ApiUser, UnsafeUserToken] | None:
        header = str(_setting("UNSAFE_USER_HEADER", DEFAULT_UNSAFE_USER_HEADER))
        raw_value = request.headers.get(header)
        if raw_value is None:
            return None
        unsafe_id = self._parse_unsafe_id(header, raw_value)
        return self._resolve_user(header, unsafe_id), UnsafeUserToken(unsafe_id=unsafe_id)

    def authenticate_header(self, request: Any) -> str:
        return str(_setting("UNSAFE_USER_HEADER", DEFAULT_UNSAFE_USER_HEADER))

    @staticmethod
    def _parse_unsafe_id(header: str, raw_value: str) -> int:
        value = raw_value.strip()
        if not value.isascii() or not value.isdigit():
            raise AuthenticationFailed(f"Некорректный заголовок {header}")
        try:
            unsafe_id = int(value)
        except ValueError:
            raise AuthenticationFailed(f"Некорректный заголовок {header}") from None
        if not MIN_UNSAFE_ID <= unsafe_id <= MAX_UNSAFE_ID:
            raise AuthenticationFailed(f"Некорректный заголовок {header}")
        return unsafe_id

    @staticmethod
    def _resolve_user(header: str, unsafe_id: int) -> ApiUser:
        if bool(_setting("UNSAFE_USER_AUTO_CREATE", True)):
            user: ApiUser
            user, _ = ApiUser.objects.get_or_create(unsafe_id=unsafe_id)
            return user
        existing: ApiUser | None = ApiUser.objects.filter(unsafe_id=unsafe_id).first()
        if existing is None:
            raise AuthenticationFailed(f"Неизвестный пользователь в заголовке {header}")
        return existing


def _setting(name: str, default: object) -> Any:
    return getattr(settings, name, default)
