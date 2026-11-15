from plugin_registry.base import AppPlugin, MenuItemDefinition, PluginZone
from django.utils.translation import gettext_lazy as _


class WebprogramPlugin(AppPlugin):
    name = "webprogram"
    verbose_name = _("Brython WebProgram")
    description = _("In-browser client-side Python execution environment")
    icon = "fa fa-code"
    category = "utilities"
    zone = PluginZone.LABS
    url_namespace = "webprogram"
    url_prefix = "webprogram"
    
    menu_items = [
        MenuItemDefinition(
            label=_("Brython WebProgram"),
            url_name="webprogram:index",
            icon="fa fa-code",
            order=30,
            parent_slug="Apps",
        )
    ]
