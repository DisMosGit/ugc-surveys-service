from django.conf import settings
from django.contrib import admin
from django.urls import URLPattern, URLResolver, path, re_path
from django.views.static import serve

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
]

if settings.SERVE_MEDIA:
    urlpatterns.append(re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}))
