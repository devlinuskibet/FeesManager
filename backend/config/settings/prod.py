"""
Production settings.

Hardened for deployment. All values come from environment variables; missing
secrets raise ImproperlyConfigured at startup.
"""

from decouple import Csv, config

from .base import *  # noqa: F401,F403

DEBUG = False

# Explicit hosts only — CORS_ALLOW_ALL_ORIGINS must be False in production.
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="", cast=Csv())

# HTTPS / secure headers
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

# Use Redis cache in prod (ensure REDIS_URL is set in the environment).
if config("CACHE_BACKEND", default="redis") == "redis" and not config("REDIS_URL", default=""):
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured("REDIS_URL is required in production")  # noqa: TRY003
