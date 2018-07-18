from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LocationManagementConfig(AppConfig):
    name = 'location_management'
    verbose_name = _('Location management')
