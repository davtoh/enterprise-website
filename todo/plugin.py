from plugin_registry import AppPlugin, MenuItemDefinition
from django.utils.translation import gettext_lazy as _


class TodoPlugin(AppPlugin):
    name = "todo"
    verbose_name = _("Todo Task Manager")
    description = _("Interactive task management app with due dates and completion states")
    icon = "fa fa-tasks"
    category = "productivity"
    
    menu_items = [
        MenuItemDefinition(
            label=_("Todo List"),
            url_name="todo:index",
            icon="fa fa-tasks",
            order=10,
            parent_slug="Apps",
        )
    ]
