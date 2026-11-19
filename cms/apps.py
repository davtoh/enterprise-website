from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CmsConfig(AppConfig):
    """Django AppConfig for the Wagtail Hybrid CMS & Blog engine."""

    default_auto_field = "django.db.models.AutoField"
    name = "cms"
    verbose_name = _("Content Management (Wagtail)")

    def ready(self):
        from .signals import register_cms_signals

        register_cms_signals()
