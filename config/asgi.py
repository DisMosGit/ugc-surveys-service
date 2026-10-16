import os

from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.asgi import get_asgi_application
from django.core.handlers.asgi import ASGIHandler

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def build_application(serve_static: bool) -> ASGIHandler:
    application = get_asgi_application()

    return ASGIStaticFilesHandler(application) if serve_static else application


def build_default_application() -> ASGIHandler:
    return build_application(settings.SERVE_STATIC)


application = build_default_application()
