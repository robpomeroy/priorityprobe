import contextlib
import os
import sys
import tempfile
import uuid
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
        SECRET_KEY = "django-insecure-dev-key-prioritysuite-framework-2026"  # nosec B105
    else:
        raise ValueError("DJANGO_SECRET_KEY must be set in production (when DEBUG is False).")

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")
    if h.strip()
]

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

@contextlib.contextmanager
def migration_lock(lock_path: Path):
    """Process-shared advisory file lock supporting POSIX (fcntl) and Windows (msvcrt).

    Raises RuntimeError if lock acquisition fails to prevent uncoordinated concurrent migrations.
    """
    with open(lock_path, "a+b") as lock_file:
        if sys.platform == "win32":
            try:
                import msvcrt

                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            except OSError as err:
                raise RuntimeError(
                    f"Failed to acquire database migration lock on {lock_path}: {err}"
                ) from err
            try:
                yield
            finally:
                try:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
        else:
            try:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            except OSError as err:
                raise RuntimeError(
                    f"Failed to acquire database migration lock on {lock_path}: {err}"
                ) from err
            try:
                yield
            finally:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass


def migrate_legacy_sqlite_database(
    user_data_dir: Path | str, legacy_temp_dir: Path | str
) -> Path:
    """Migrate legacy SQLite database from temp directory to user data directory.

    Serialises migration with a process-shared lock to prevent concurrent worker
    races. Recovers hot journals and creates a consistent destination database
    via SQLite's backup API. Staged in a temporary file and published atomically.
    Aborts startup if migration fails to prevent data loss.
    """
    user_data_path = Path(user_data_dir)
    user_data_path.mkdir(parents=True, exist_ok=True, mode=0o700)
    sqlite_db_path = user_data_path / "prioritysuite_dev.sqlite3"
    legacy_temp_db = Path(legacy_temp_dir) / "prioritysuite_dev.sqlite3"

    # Fast-path check: return immediately if target exists or no legacy DB
    if sqlite_db_path.exists() or not legacy_temp_db.is_file():
        return sqlite_db_path

    lock_path = user_data_path / ".migration.lock"
    with migration_lock(lock_path):
        # Recheck destination existence after acquiring process lock
        if sqlite_db_path.exists() or not legacy_temp_db.is_file():
            return sqlite_db_path

        temp_target = sqlite_db_path.with_name(
            f"prioritysuite_dev_{os.getpid()}_{uuid.uuid4().hex[:8]}.tmp"
        )
        try:
            import sqlite3

            source_conn = sqlite3.connect(str(legacy_temp_db))
            try:
                dest_conn = sqlite3.connect(str(temp_target))
                try:
                    source_conn.backup(dest_conn)
                finally:
                    dest_conn.close()
            finally:
                source_conn.close()

            # Verify destination still does not exist immediately before publishing
            if sqlite_db_path.exists():
                temp_target.unlink()
                return sqlite_db_path

            temp_target.replace(sqlite_db_path)
        except Exception as err:
            if temp_target.exists():
                try:
                    temp_target.unlink()
                except OSError:
                    pass
            raise RuntimeError(
                f"Failed to migrate legacy SQLite database from {legacy_temp_db} to "
                f"{sqlite_db_path}: {err}"
            ) from err

    return sqlite_db_path


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
    sqlite_env_path = os.environ.get("SQLITE_PATH", "")
    if not sqlite_env_path:
        if str(BASE_DIR).startswith("\\\\"):
            user_data_dir = Path.home() / ".local" / "share" / "prioritysuite"
            legacy_temp_dir = os.environ.get("TEMP") or tempfile.gettempdir()
            sqlite_db_path = migrate_legacy_sqlite_database(user_data_dir, legacy_temp_dir)
        else:
            sqlite_db_path = default_sqlite_path
    else:
        sqlite_db_path = Path(sqlite_env_path)

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(sqlite_db_path),
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
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
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", str(not DEBUG)).lower() in (
    "true",
    "1",
    "yes",
)
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", str(not DEBUG)).lower() in (
    "true",
    "1",
    "yes",
)

# Allowlisted Ollama hosts in hosted deployments
# (comma-separated, e.g. "ollama,host.docker.internal")
OLLAMA_ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("OLLAMA_ALLOWED_HOSTS", "").split(",") if h.strip()
]

# Encryption key for sensitive fields (BYOK API keys)
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")
