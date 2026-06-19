"""
Test settings — extends base settings but swaps Postgres for SQLite in-memory.
Used automatically by pytest when DJANGO_SETTINGS_MODULE=config.settings_test.

In Docker/CI the full Postgres container is used (set DJANGO_SETTINGS_MODULE=config.settings).
"""
from config.settings import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
