from plugin_registry import AppPlugin, MenuItemDefinition


class LanguageManagementPlugin(AppPlugin):
    """Plugin definition for Language Management and Translation."""

    name = "language_management"
    verbose_name = "Language & Localization"
    description = "Internationalization, catalog maintenance, and automated translation."
    category = "utilities"
    icon = "fa-language"

    url_namespace = "language_management"
    url_prefix = "lang"

    tasks = [
        "task_runner.run_auto_translate",
    ]
