from django.core.management.base import BaseCommand
from menu_management.sync import sync_plugin_menus


class Command(BaseCommand):
    help = 'Synchronize installed AppPlugins into Menu and MenuItem models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--menu',
            default='main_navbar',
            help='Slug of the menu to synchronize into (default: main_navbar)'
        )

    def handle(self, *args, **options):
        menu_slug = options['menu']
        self.stdout.write(f"Syncing plugin menu items into '{menu_slug}'...")
        sync_plugin_menus(menu_slug)
        self.stdout.write(self.style.SUCCESS(f"Successfully synced plugins into menu '{menu_slug}'."))
