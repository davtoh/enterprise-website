from plugin_registry.base import AppPlugin, MenuItemDefinition


class TaskRunnerPlugin(AppPlugin):
    """Plugin definition for the Celery background task runner."""

    name = "task_runner"
    verbose_name = "Background Task Runner"
    description = "Asynchronous task queue with live WebSocket progress streaming."
    category = "utilities"
    icon = "fa-tasks"

    url_namespace = "task_runner"
    url_prefix = "tasks"

    menu_items = [
        MenuItemDefinition(
            label="Background Tasks",
            url_name="task_runner:list",
            icon="fa fa-tasks",
            order=45,
            parent_slug="Apps",
            requires_auth=True,
            requires_staff=True,
        ),
    ]

    tasks = [
        "task_runner.run_auto_translate",
        "task_runner.run_collectstatic",
        "task_runner.run_external_script",
    ]
