"""
Configuracion de Django.

Todo lo que cambia entre entornos entra por variables de entorno. El motor de
base de datos se resuelve exclusivamente desde DATABASE_URL: migrar a Postgres
o MySQL no deberia requerir tocar este fichero.
"""
from pathlib import Path
import os

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, "1" if default else "0").strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------- basico
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "inseguro-solo-para-desarrollo")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:8080").split(",") if o.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

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

# ----------------------------------------------------------------- base de datos
# SQLite es el motor por defecto y una decision temporal. El timeout alto y el
# modo WAL (ver core/apps.py) son lo que hace tolerable que django y api
# compartan el mismo fichero. Ver docs/DECISIONES.md, seccion 3.
DATABASES = {
    "default": dj_database_url.parse(
        os.getenv("DATABASE_URL", "sqlite:////data/db.sqlite3"),
        conn_max_age=env_int("DB_CONN_MAX_AGE", 60),
    )
}
if DATABASES["default"]["ENGINE"].endswith("sqlite3"):
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"]["timeout"] = env_int("DB_BUSY_TIMEOUT_SECONDS", 30)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "core.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------------------------------- i18n y estaticos
LANGUAGE_CODE = os.getenv("DJANGO_LANGUAGE_CODE", "es")
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Los PDF viven en el volumen compartido para que el servicio api pueda leerlos.
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "/data/media"))

# ------------------------------------------------------------------------ jwt
# El mismo secreto lo valida FastAPI. Es lo que sostiene el aislamiento entre
# tenants: tenant_id viaja firmado y el servicio de IA no lo acepta de ningun
# otro sitio. Ver docs/ARQUITECTURA.md, seccion 6.
JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_TTL_MINUTES = env_int("JWT_TTL_MINUTES", 60)
JWT_ISSUER = os.getenv("JWT_ISSUER", "atyt-assistant-django")

# ------------------------------------------------------------------ ingesta
CHUNK_SIZE_CHARS = env_int("CHUNK_SIZE_CHARS", 900)
CHUNK_OVERLAP_CHARS = env_int("CHUNK_OVERLAP_CHARS", 150)

# -------------------------------------------------------------- datos de ejemplo
SEED_PROFILE = os.getenv("SEED_PROFILE", "full").strip().lower()
SEED_TENANTS = env_int("SEED_TENANTS", 40)
SEED_RANDOM_SEED = env_int("SEED_RANDOM_SEED", 20260724)

# --------------------------------------------------------------------- seguridad
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", False)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "[{levelname}] {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}
