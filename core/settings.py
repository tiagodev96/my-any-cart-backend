from corsheaders.defaults import default_headers
from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url
from datetime import timedelta

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _split_env_list(name: str, default: str = ""):
    return [
        v.strip()
        for v in os.getenv(name, default).split(",")
        if v.strip()
    ]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-unsafe")
DEBUG = os.getenv("DEBUG", "1") == "1"
ALLOWED_HOSTS = _split_env_list(
    "ALLOWED_HOSTS", "localhost,127.0.0.1,.vercel.app")

# --- Apps ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3rd party
    "rest_framework",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    # local
    "cart",
]

# --- Middleware ---
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# --- URLs/WSGI/ASGI ---
ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "api.wsgi.app"
ASGI_APPLICATION = "core.asgi.application"

# --- Templates ---
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.debug",
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ],
    },
}]

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=os.getenv("DB_SSL_REQUIRE", "0") == "1",
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(BASE_DIR / "db.sqlite3"),
        }
    }

# --- DRF ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS":
        "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

# --- Simple JWT ---
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# --- CORS / CSRF ---
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = _split_env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,"
    "https://my-any-cart-wduh.vercel.app,"
    "https://*.vercel.app"
)
CORS_ALLOW_CREDENTIALS = True


CORS_ALLOW_HEADERS = list(default_headers) + [
    "authorization",
    "content-type",
    "idempotency-key"
]

CSRF_TRUSTED_ORIGINS = _split_env_list(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:3000,"
    "http://127.0.0.1:3000,"
    "https://my-any-cart-wduh.vercel.app,"
    "https://*.vercel.app"
)

# --- Google OAuth2 ---
GOOGLE_CLIENT_IDS = [
    s.strip()
    for s in os.getenv(
        "GOOGLE_CLIENT_IDS",
        os.getenv("GOOGLE_CLIENT_ID", ""),
    ).split(",")
    if s.strip()
]

# --- Static files ---
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- Password validation ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME":
        (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
     },
    {"NAME":
        "django.contrib.auth.password_validation.MinimumLengthValidator",
     },
    {"NAME":
        "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME":
        "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- I18N / TZ ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- Auto field ---
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Logging ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO" if not DEBUG else "DEBUG",
    },
}
