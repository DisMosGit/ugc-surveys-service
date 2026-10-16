from pathlib import Path
from typing import Any

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env.read_env(env.str("DJANGO_ENV_FILE", default=str(BASE_DIR / ".env")))


def _list(value: str) -> list[str]:
    return [item for item in value.split(",") if item]


def _path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else BASE_DIR / path


DEBUG = env.bool("DJANGO_DEBUG", default=True)
SECRET_KEY = env.str("DJANGO_SECRET_KEY")

ALLOWED_HOSTS = _list(env.str("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1,[::1]"))
CSRF_TRUSTED_ORIGINS = _list(
    env.str(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        default="http://localhost,http://localhost:8000,http://127.0.0.1,http://127.0.0.1:8000",
    )
)

LOG_LEVEL = env.str("DJANGO_LOG_LEVEL", default="INFO")
DATA_DIR = _path(env.str("DJANGO_DATA_DIR", default=str(BASE_DIR / "data")))
LOG_DIR = _path(env.str("DJANGO_LOG_DIR", default=str(DATA_DIR / "logs")))
LOG_FILE = _path(env.str("DJANGO_LOG_FILE", default=str(LOG_DIR / "django.log")))
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "DEBUG",
        },
        "file": {
            "class": "logging.FileHandler",
            "formatter": "simple",
            "level": "DEBUG",
            "filename": LOG_FILE,
            "encoding": "utf-8",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}

STATIC_URL = "static/"
STATIC_ROOT = DATA_DIR / "static"
MEDIA_URL = "media/"
MEDIA_ROOT = DATA_DIR / "media"
SERVE_STATIC = env.bool("DJANGO_SERVE_STATIC", default=True)
SERVE_MEDIA = env.bool("DJANGO_SERVE_MEDIA", default=True)

for _directory in (DATA_DIR / "db", LOG_DIR, LOG_FILE.parent, STATIC_ROOT, MEDIA_ROOT):
    _directory.mkdir(parents=True, exist_ok=True)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "core",
    "accounts",
    "surveys",
    "answers",
    "analytics",
]

AUTH_USER_MODEL = "accounts.AdminUser"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

if env.str("DB_USER", default=""):
    pool_options: dict[str, Any] = {}
    if env.bool("DB_POOL", default=True):
        pool_options = {
            "min_size": env.int("DB_POOL_MIN_SIZE", default=2),
            "max_size": env.int("DB_POOL_MAX_SIZE", default=8),
            "timeout": env.float("DB_POOL_TIMEOUT", default=10.0),
            "max_lifetime": env.float("DB_POOL_MAX_LIFETIME", default=1800.0),
        }
    DATABASES: dict[str, dict[str, Any]] = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env.str("DB_NAME", default="ugc_surveys"),
            "USER": env.str("DB_USER", default=""),
            "PASSWORD": env.str("DB_PASSWORD", default=""),
            "HOST": env.str("DB_HOST", default="localhost"),
            "PORT": env.str("DB_PORT", default="5432"),
            "CONN_MAX_AGE": 0 if pool_options else env.int("DB_CONN_MAX_AGE", default=600),
            "CONN_HEALTH_CHECKS": env.bool("DB_CONN_HEALTH_CHECKS", default=True),
            "OPTIONS": {"pool": pool_options} if pool_options else {},
        },
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": DATA_DIR / "db" / "db.sqlite3",
        },
    }

LANGUAGE_CODE = "ru-RU"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.UnsafeUserAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "config.exceptions.api_exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "config.renderers.OrjsonRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
    ],
}

UNSAFE_USER_HEADER = env.str("UNSAFE_USER_HEADER", default="X-Unsafe-User-Id")
UNSAFE_USER_AUTO_CREATE = env.bool("UNSAFE_USER_AUTO_CREATE", default=True)
