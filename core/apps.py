import atexit

from django.apps import AppConfig
from django.db import connections


class CoreConfig(AppConfig):
    name = "core"

    def ready(self) -> None:
        atexit.register(_close_connection_pools)


def _close_connection_pools() -> None:
    for connection in connections.all(initialized_only=True):
        close_pool = getattr(connection, "close_pool", None)
        if callable(close_pool):
            close_pool()
