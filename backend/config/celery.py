"""Celery configuration for the School Fee & Payment Tracker."""

import os

from celery import Celery

# Default to dev settings so `celery -A config worker` works out of the box.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("schoolpay")

# Read all CELERY_* settings from Django settings.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in every installed app.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task: prints the Celery request. Useful to verify a worker works."""
    print(f"Request: {self.request!r}")
