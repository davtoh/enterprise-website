from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ThemeManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'theme_management'
    verbose_name = _('Theme & CSS Framework Management')
