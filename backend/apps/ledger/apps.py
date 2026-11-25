"""App configuration for the ledger app."""

from django.apps import AppConfig


class LedgerConfig(AppConfig):
    """Django AppConfig for append-only student fee ledger."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ledger"
    verbose_name = "Ledger"
