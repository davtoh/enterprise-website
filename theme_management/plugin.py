from plugin_registry.base import AppPlugin, MenuItemDefinition


class ThemeManagementPlugin(AppPlugin):
    name = "theme_management"
    verbose_name = "Theme & CSS Framework Manager"
    description = "Dynamic CSS framework selector and multi-theme architecture."
    version = "1.0.0"
    icon = "fa-paint-brush"
    category = "core"
    url_namespace = "theme_management"
    url_prefix = "theme/"
