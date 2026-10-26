from django.utils.translation import gettext_lazy as _
from plugin_registry.base import AppPlugin, MenuItemDefinition


class IntelligentTrackerPlugin(AppPlugin):
    """
    Plugin definition for Intelligent Tracker Edge AI Security Hub module.
    Exposes security operations in dynamic menus and defines integration endpoints.
    """

    name = "intelligent_tracker_hub"
    verbose_name = _("Edge AI Security Hub")
    description = _(
        "Spatial security command hub integrating real-time edge AI vision, "
        "intrusion webhooks, video evidence archiving, and access control."
    )
    category = "productivity"
    icon = "fa fa-shield"

    url_namespace = "intelligent_tracker_hub"
    url_prefix = "security"

    menu_items = [
        MenuItemDefinition(
            label=_("Security Hub"),
            url_name="intelligent_tracker_hub:dashboard",
            icon="fa fa-shield",
            order=33,
            parent_slug="Apps",
            requires_auth=True,
        ),
    ]

    settings_defaults = {
        "INTELLIGENT_TRACKER_SECRET_KEY": "default-dev-tracker-secret-key-change-in-prod",
    }
