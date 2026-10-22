from plugin_registry import AppPlugin, MenuItemDefinition
from django.utils.translation import gettext_lazy as _


class PollsPlugin(AppPlugin):
    name = "polls"
    verbose_name = _("Polls & Voting")
    description = _("Interactive voting system with fraud prevention and results charts")
    icon = "fa fa-bar-chart"
    category = "engagement"
    
    menu_items = [
        MenuItemDefinition(
            label=_("Polls"),
            url_name="polls:index",
            icon="fa fa-bar-chart",
            order=20,
            parent_slug="Apps",
        )
    ]
