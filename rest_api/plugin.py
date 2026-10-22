from plugin_registry import AppPlugin, MenuItemDefinition
from django.utils.translation import gettext_lazy as _


class RestApiPlugin(AppPlugin):
    name = "rest_api"
    verbose_name = _("REST API")
    description = _("Django REST Framework browsable and serialized endpoints")
    icon = "fa fa-cogs"
    category = "utilities"
    
    menu_items = [
        MenuItemDefinition(
            label=_("REST API"),
            url_path="/rest_api/",
            icon="fa fa-cogs",
            order=40,
            parent_slug="Apps",
        )
    ]
