from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class IntelligentTrackerHubConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "intelligent_tracker_hub"
    verbose_name = _("Intelligent Tracker Security Hub")
