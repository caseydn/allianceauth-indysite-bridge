from django.apps import AppConfig


class IndustrysiteConfig(AppConfig):
    name = "industrysite"
    label = "industrysite"
    verbose_name = "Industry Site"
    default_auto_field = "django.db.models.AutoField"

    def ready(self):
        # Wire the group-change signal so role/affiliation updates re-push.
        from . import signals  # noqa: F401
