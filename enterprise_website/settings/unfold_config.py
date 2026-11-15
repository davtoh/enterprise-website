"""
Django Unfold admin theme and sidebar navigation configuration.

Organizes enterprise admin models into domain groups (CRM, ERP, Security Hub,
Platform, CMS) with quick cross-links to the Module Marketplace, Rosetta, and CMS.
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

UNFOLD = {
    "SITE_TITLE": _("Enterprise Admin"),
    "SITE_HEADER": _("Enterprise Workspace"),
    "SITE_SUBHEADER": _("Modular Platform & Admin"),
    "SITE_SYMBOL": "grid_view",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": _("Platform"),
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                    {
                        "title": _("Module Marketplace"),
                        "icon": "extension",
                        "link": reverse_lazy("admin_marketplace"),
                    },
                    {
                        "title": _("Plugin States"),
                        "icon": "toggle_on",
                        "link": reverse_lazy("admin:plugin_registry_pluginstate_changelist"),
                    },
                    {
                        "title": _("Task Jobs"),
                        "icon": "bolt",
                        "link": reverse_lazy("admin:task_runner_taskjob_changelist"),
                    },
                    {
                        "title": _("Users"),
                        "icon": "group",
                        "link": reverse_lazy("admin:user_management_siteuser_changelist"),
                    },
                    {
                        "title": _("Navigation Menus"),
                        "icon": "menu",
                        "link": reverse_lazy("admin:menu_management_menu_changelist"),
                    },
                ],
            },
            {
                "title": _("CRM"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Contacts"),
                        "icon": "contacts",
                        "link": reverse_lazy("admin:crm_contact_changelist"),
                    },
                    {
                        "title": _("Companies"),
                        "icon": "business",
                        "link": reverse_lazy("admin:crm_company_changelist"),
                    },
                    {
                        "title": _("Leads"),
                        "icon": "trending_up",
                        "link": reverse_lazy("admin:crm_lead_changelist"),
                    },
                    {
                        "title": _("Email Sequences"),
                        "icon": "mail",
                        "link": reverse_lazy("admin:crm_emailsequence_changelist"),
                    },
                ],
            },
            {
                "title": _("ERP"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Products"),
                        "icon": "inventory_2",
                        "link": reverse_lazy("admin:erp_product_changelist"),
                    },
                    {
                        "title": _("Invoices"),
                        "icon": "receipt_long",
                        "link": reverse_lazy("admin:erp_invoice_changelist"),
                    },
                    {
                        "title": _("Stock Movements"),
                        "icon": "swap_horiz",
                        "link": reverse_lazy("admin:erp_stockmovement_changelist"),
                    },
                ],
            },
            {
                "title": _("Security Hub"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Security Events"),
                        "icon": "security",
                        "link": reverse_lazy("admin:intelligent_tracker_hub_securityevent_changelist"),
                    },
                    {
                        "title": _("Cameras"),
                        "icon": "videocam",
                        "link": reverse_lazy("admin:intelligent_tracker_hub_camera_changelist"),
                    },
                    {
                        "title": _("Visitor Access Logs"),
                        "icon": "badge",
                        "link": reverse_lazy("admin:intelligent_tracker_hub_visitoraccesslog_changelist"),
                    },
                ],
            },
            {
                "title": _("CMS & Localization"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("CMS"),
                        "icon": "article",
                        "link": "/cms/",
                    },
                    {
                        "title": _("Rosetta Translations"),
                        "icon": "translate",
                        "link": "/rosetta/",
                    },
                ],
            },
        ],
    },
}
