from plugin_registry import AppPlugin, MenuItemDefinition
from django.utils.translation import gettext_lazy as _


class WebprogramPlugin(AppPlugin):
    name = "webprogram"
    verbose_name = _("Brython WebProgram")
    description = _("In-browser client-side Python execution environment")
    icon = "fa fa-code"
    category = "utilities"
    
    menu_items = [
        MenuItemDefinition(
            label=_("Brython WebProgram"),
            url_name="webprogram:index",
            icon="fa fa-code",
            order=30,
            parent_slug="Apps",
        )
    ]
