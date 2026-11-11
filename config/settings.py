import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure LiteLLM uses bundled offline cost map without remote network fetches
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")

# Quick-start development settings - unsuitable for production
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-dev-key-prioritysuite-framework-2026"
    else:
        raise ValueError("DJANGO_SECRET_KEY must be set in production (when DEBUG is False).")

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",") if h.strip()]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local Apps
    "accounts.apps.AccountsConfig",
    "frameworks.apps.FrameworksConfig",
    "decisions.apps.DecisionsConfig",
    "llm.apps.LlmConfig",
    "exports.apps.ExportsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.csrf",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.user_preferences",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database configuration: defaults to SQLite, supports MariaDB/MySQL via env
DB_ENGINE = os.environ.get("DATABASE_ENGINE", "sqlite").lower()

if DB_ENGINE in ("mysql", "mariadb"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ.get("DB_NAME", "prioritysuite"),
            "USER": os.environ.get("DB_USER", "prioritysuite"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("DB_PORT", "3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
            },
        }
    }
else:
    # On Windows over 9P/SMB network paths (e.g. \\wsl.localhost), SQLite POSIX file locking
    # fails unless located on a native Windows path or configured with custom path.
    # We allow configuring SQLITE_PATH or fallback gracefully.
    default_sqlite_path = BASE_DIR / "db.sqlite3"
    # If BASE_DIR is UNC path, use TEMP directory for SQLite to prevent UNC SMB locking failures
    sqlite_db_path = os.environ.get("SQLITE_PATH", "")
    if not sqlite_db_path:
        if str(BASE_DIR).startswith("\\\\"):
            temp_dir = Path(os.environ.get("TEMP", "/tmp"))
            sqlite_db_path = temp_dir / "prioritysuite_dev.sqlite3"
        else:
            sqlite_db_path = default_sqlite_path
    else:
        sqlite_db_path = Path(sqlite_db_path)

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": sqlite_db_path,
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Auth Redirects
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "frameworks:workspace"
LOGOUT_REDIRECT_URL = "accounts:login"

# Trust X-Forwarded-Proto from reverse proxy (e.g. Nginx TLS terminator)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# Allowlisted Ollama hosts in hosted deployments (comma-separated, e.g. "ollama,host.docker.internal")
OLLAMA_ALLOWED_HOSTS = [h.strip() for h in os.environ.get("OLLAMA_ALLOWED_HOSTS", "").split(",") if h.strip()]

# Encryption key for sensitive fields (BYOK API keys)
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")
