from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PluginRegistryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plugin_registry'
    verbose_name = _('Plugin Registry')

    def ready(self):
        from .registry import registry
        registry.autodiscover()
