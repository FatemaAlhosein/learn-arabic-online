from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        """Register signal handlers when Django starts.

        Importing the module is enough — the @receiver decorators inside
        signals.py do the actual registration.
        """
        from . import signals  # noqa: F401
