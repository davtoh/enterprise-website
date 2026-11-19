"""Interactive and non-interactive `manage.py create_site` scaffolding wizard."""

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils.translation import gettext as _

from plugin_registry.scaffolding.cli_runner import (
    add_scaffolding_arguments,
    execute_scaffolding,
)


class Command(BaseCommand):
    """Scaffold a standalone composable Django site from this enterprise template."""

    help = _("Create a standalone composable Django project from a SiteManifest or interactive wizard.")

    def add_arguments(self, parser: CommandParser) -> None:
        add_scaffolding_arguments(parser)

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            execute_scaffolding(options, stdout=self.stdout)
        except (FileExistsError, ValueError, OSError) as exc:
            raise CommandError(str(exc)) from exc
