import logging
from django.db import transaction
from plugin_registry import registry
from .models import Menu, MenuItem

logger = logging.getLogger(__name__)


def sync_plugin_menus(menu_slug: str = 'main_navbar'):
    """
    Synchronizes discovered AppPlugins with MenuItem models in the database.
    Idempotent: preserves custom user ordering, titles, and visibility changes,
    while ensuring newly installed plugin menu items exist.
    """
    registry.autodiscover()
    plugins = registry.get_all_plugins()

    with transaction.atomic():
        menu, _ = Menu.objects.get_or_create(
            slug=menu_slug,
            defaults={'title': 'Main Navigation', 'is_active': True}
        )

        # Ensure Apps parent container exists
        apps_parent = MenuItem.objects.filter(menu=menu, title='Apps').first()
        if not apps_parent:
            apps_parent = MenuItem.objects.create(
                menu=menu,
                title='Apps',
                url_name='',
                url_path='#',
                order=60,
                is_custom=False,
                plugin_source='system'
            )

        # Ensure Site Admin item exists under Apps for staff users
        admin_item = MenuItem.objects.filter(menu=menu, url_name='admin:index').first()
        if not admin_item:
            MenuItem.objects.create(
                menu=menu,
                parent=apps_parent,
                title='Site Admin',
                url_name='admin:index',
                url_path='/admin/',
                icon='fa fa-shield',
                order=50,
                requires_auth=True,
                requires_staff=True,
                plugin_source='system',
                is_custom=False,
            )

        for plugin_name, plugin_cls in plugins.items():
            for item_def in plugin_cls.get_menu_items():
                # Check parent if specified by slug/title
                parent_item = None
                if item_def.parent_slug:
                    parent_item = MenuItem.objects.filter(
                        menu=menu,
                        url_name=item_def.parent_slug
                    ).first() or MenuItem.objects.filter(
                        menu=menu,
                        title=item_def.parent_slug
                    ).first()

                    # Auto-create parent category container if not present
                    if not parent_item:
                        parent_item = MenuItem.objects.create(
                            menu=menu,
                            title=item_def.parent_slug,
                            url_name='',
                            url_path='#',
                            order=50,
                            is_custom=False,
                            plugin_source='system'
                        )

                # Look up existing item by plugin_source and url_name/path
                lookup_kwargs = {'menu': menu, 'plugin_source': plugin_name}
                if item_def.url_name:
                    lookup_kwargs['url_name'] = item_def.url_name
                else:
                    lookup_kwargs['url_path'] = item_def.url_path

                existing = MenuItem.objects.filter(**lookup_kwargs).first()

                if not existing:
                    MenuItem.objects.create(
                        menu=menu,
                        parent=parent_item,
                        title=item_def.label,
                        url_name=item_def.url_name,
                        url_path=item_def.url_path,
                        icon=item_def.icon,
                        order=item_def.order,
                        requires_auth=item_def.requires_auth,
                        requires_staff=item_def.requires_staff,
                        plugin_source=plugin_name,
                        is_custom=False,
                    )
                    logger.info("Created menu item for plugin: %s (%s)", plugin_name, item_def.label)
                elif not existing.is_custom:
                    updated = False
                    if existing.parent != parent_item:
                        existing.parent = parent_item
                        updated = True
                    if existing.icon != item_def.icon:
                        existing.icon = item_def.icon
                        updated = True
                    if existing.requires_staff != item_def.requires_staff:
                        existing.requires_staff = item_def.requires_staff
                        updated = True
                    if existing.requires_auth != item_def.requires_auth:
                        existing.requires_auth = item_def.requires_auth
                        updated = True
                    if updated:
                        existing.save()
                        logger.info("Updated menu item for plugin: %s (%s)", plugin_name, item_def.label)
