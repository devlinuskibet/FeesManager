"""
Development settings.

Safe defaults for local development on Windows. Never use these values in
production — secrets must come from .env / real environment variables.
"""

from .base import *  # noqa: F401,F403
from .base import BASE_DIR  # noqa: F401  (explicit import to satisfy ruff F405)

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Allow the React dev server (Vite default port 5173) to call the API.
CORS_ALLOW_ALL_ORIGINS = True
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Console email backend: emails are printed to stdout instead of sent.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Run Celery tasks inline so developers do not need Redis running to test.
# Flip CELERY_TASK_ALWAYS_EAGER=False in .env to use a real worker.
CELERY_TASK_ALWAYS_EAGER = True

INTERNAL_IPS = ["127.0.0.1", "localhost"]

# Local development database. SQLite is used by default so you can run and test
# immediately on Windows without Docker/PostgreSQL. When you are ready for the
# production stack, switch back to PostgreSQL (configured in base.py) and start
# Postgres/Redis with `docker compose up -d` from the schoolpay folder.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
