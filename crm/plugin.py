from django.utils.translation import gettext_lazy as _
from plugin_registry.base import AppPlugin, MenuItemDefinition


class CRMPlugin(AppPlugin):
    """Plugin definition for Customer Relationship Management (CRM) module."""

    name = "crm"
    verbose_name = _("Customer Relationship Management")
    description = _("Full-featured CRM with pipeline Kanban, email sequences, customer segmentation, and analytics.")
    category = "productivity"
    icon = "fa fa-users"

    url_namespace = "crm"
    url_prefix = "crm"

    menu_items = [
        MenuItemDefinition(
            label=_("CRM"),
            url_name="crm:dashboard",
            icon="fa fa-users",
            order=32,
            parent_slug="Apps",
            requires_auth=True,
        ),
    ]

    tasks = [
        "crm.process_email_sequences",
        "crm.send_segment_broadcast",
    ]
