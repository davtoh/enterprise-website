from django.utils.translation import gettext_lazy as _

from plugin_registry import AppPlugin, PluginZone


class CMSPlugin(AppPlugin):
    """System plugin registering the Wagtail CMS & Blog engine."""

    name = "cms"
    verbose_name = _("Wagtail CMS & Blog")
    description = _(
        "Hierarchical Wagtail CMS pages, StreamField block composer, "
        "multilingual localization, and enterprise blog."
    )
    category = "core"
    icon = "fa-newspaper-o"
    zone = PluginZone.PUBLIC
    is_system = True
    url_namespace = "wagtailadmin_home"
    url_prefix = "cms/"
    menu_items = []
