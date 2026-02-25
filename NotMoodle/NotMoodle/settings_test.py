"""
Test Settings for NotMoodle

Inherits from base settings and overrides for faster, isolated testing.
"""
import os
from pathlib import Path
from .settings import *  # noqa

# Override BASE_DIR if needed (should be same as base settings)
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================
# SECURITY (Tests Only)
# ============================
SECRET_KEY = "test-secret-key-not-for-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]

# ============================
# DATABASE
# ============================
# Use PostgreSQL if configured, otherwise fallback to SQLite
if os.environ.get("USE_SQLITE", "true").lower() == "false":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "notmoodle_test"),
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "postgres"),
            "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "ATOMIC_REQUESTS": True,
        }
    }
    USING_POSTGRESQL = True
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
            "ATOMIC_REQUESTS": True,
        }
    }
    USING_POSTGRESQL = False

# ============================
# PASSWORD HASHING
# ============================
# Use fast (insecure) password hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ============================
# EMAIL
# ============================
# Use in-memory email backend (no actual emails sent)
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# ============================
# CACHES
# ============================
# Disable caching in tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# ============================
# MEDIA & STATIC FILES
# ============================
# Use temporary directories for media files in tests
import tempfile
MEDIA_ROOT = Path(tempfile.gettempdir()) / "notmoodle_test_media"
MEDIA_URL = "/media/"

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = Path(tempfile.gettempdir()) / "notmoodle_test_static"

# ============================
# LOGGING
# ============================
# Reduce logging noise during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}

# ============================
# SOCIAL AUTH (Google OAuth)
# ============================
# Disable social auth during tests to avoid external calls
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = "test-oauth-key"
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = "test-oauth-secret"

# ============================
# AI ASSISTANT (Ollama)
# ============================
# Use mock Ollama endpoints in tests
OLLAMA_BASE_URL = "http://localhost:11434"
AI_CHAT_MODEL = "llama3.1:latest"
AI_EMBED_MODEL = "nomic-embed-text"
AI_DAILY_QUESTION_LIMIT = 100

# ============================
# CELERY (if used in future)
# ============================
# CELERY_TASK_ALWAYS_EAGER = True
# CELERY_TASK_EAGER_PROPAGATES = True

# ============================
# CSRF & SECURITY
# ============================
# Disable CSRF checks in tests
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# ============================
# TIMEZONE
# ============================
USE_TZ = True
TIME_ZONE = "UTC"

# ============================
# TESTS-SPECIFIC FLAGS
# ============================
TESTING = True

# Print confirmation
print("[+] Test settings loaded with", "PostgreSQL" if USING_POSTGRESQL else "SQLite in-memory database")

