from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UserManagementConfig(AppConfig):
    name = 'user_management'
    verbose_name = _("User management")