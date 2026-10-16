from typing import Any

from rest_framework.response import Response
from rest_framework.views import exception_handler

from core.exceptions import DomainError


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, DomainError):
        return Response({"detail": str(exc)}, status=exc.status_code)
    return exception_handler(exc, context)
