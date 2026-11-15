import logging
from django.db import transaction
from plugin_registry import registry
from .cache import invalidate_menu_cache
from .models import Menu, MenuItem

logger = logging.getLogger(__name__)


def _ensure_apps_and_admin_items(menu: Menu) -> None:
    """Ensure the default 'Apps' container and staff-only 'Site Admin' link exist."""
    apps_parent = MenuItem.objects.filter(menu=menu, title='Apps').first()
    if not apps_parent:
        apps_parent = MenuItem.objects.create(
            menu=menu,
            title='Apps',
            url_name='',
            url_path='#',
            order=60,
            is_custom=False,
            plugin_source='system',
        )

    if not MenuItem.objects.filter(menu=menu, url_name='admin:index').exists():
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


def _resolve_parent_item(menu: Menu, parent_slug: str | None) -> MenuItem | None:
    """Find or auto-create a parent MenuItem container for a given parent_slug."""
    if not parent_slug:
        return None
    parent_item = (
        MenuItem.objects.filter(menu=menu, url_name=parent_slug).first()
        or MenuItem.objects.filter(menu=menu, title=parent_slug).first()
    )
    if parent_item:
        return parent_item
    return MenuItem.objects.create(
        menu=menu,
        title=parent_slug,
        url_name='',
        url_path='#',
        order=50,
        is_custom=False,
        plugin_source='system',
    )


def _update_menu_item_if_needed(
    existing: MenuItem,
    parent_item: MenuItem | None,
    item_def,
    requires_auth: bool,
    requires_staff: bool,
    plugin_name: str,
) -> None:
    """Update non-custom MenuItem fields when plugin metadata has changed."""
    if existing.is_custom:
        return
    updates = {
        'parent': parent_item,
        'icon': item_def.icon,
        'requires_staff': requires_staff,
        'requires_auth': requires_auth,
    }
    if any(getattr(existing, field) != value for field, value in updates.items()):
        for field, value in updates.items():
            setattr(existing, field, value)
        existing.save()
        logger.info("Updated menu item for plugin: %s (%s)", plugin_name, item_def.label)


def _sync_single_menu_item(menu: Menu, plugin_name: str, plugin_cls, item_def) -> None:
    """Create or update a single plugin MenuItem, propagating plugin access defaults."""
    parent_item = _resolve_parent_item(menu, item_def.parent_slug)
    requires_auth = bool(item_def.requires_auth or getattr(plugin_cls, 'requires_auth', False))
    requires_staff = bool(item_def.requires_staff or getattr(plugin_cls, 'requires_staff', False))

    lookup_kwargs = {'menu': menu, 'plugin_source': plugin_name}
    if item_def.url_name:
        lookup_kwargs['url_name'] = item_def.url_name
    else:
        lookup_kwargs['url_path'] = item_def.url_path

    existing = MenuItem.objects.filter(**lookup_kwargs).first()
    if existing:
        _update_menu_item_if_needed(
            existing, parent_item, item_def, requires_auth, requires_staff, plugin_name
        )
        return

    MenuItem.objects.create(
        menu=menu,
        parent=parent_item,
        title=item_def.label,
        url_name=item_def.url_name,
        url_path=item_def.url_path,
        icon=item_def.icon,
        order=item_def.order,
        requires_auth=requires_auth,
        requires_staff=requires_staff,
        plugin_source=plugin_name,
        is_custom=False,
    )
    logger.info("Created menu item for plugin: %s (%s)", plugin_name, item_def.label)


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
            defaults={'title': 'Main Navigation', 'is_active': True},
        )
        _ensure_apps_and_admin_items(menu)
        for plugin_name, plugin_cls in plugins.items():
            for item_def in plugin_cls.get_menu_items():
                _sync_single_menu_item(menu, plugin_name, plugin_cls, item_def)

    try:
        from cms.bridge import sync_wagtail_menus

        sync_wagtail_menus(menu_slug=menu_slug)
    except ImportError:
        pass
    invalidate_menu_cache()
