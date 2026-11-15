from django.db.models.signals import post_delete, post_save
from wagtail.signals import page_published, page_unpublished

from menu_management.cache import invalidate_menu_cache


def _on_wagtail_page_changed(sender, **kwargs) -> None:
    """Re-sync Wagtail navigation items and invalidate cached menu trees."""
    from .bridge import sync_wagtail_menus

    sync_wagtail_menus()
    invalidate_menu_cache()


def _on_menu_or_plugin_changed(sender, **kwargs) -> None:
    """Invalidate cached menu trees whenever Menu, MenuItem, or PluginState changes."""
    invalidate_menu_cache()


def register_cms_signals() -> None:
    """Connect Wagtail page lifecycle and menu/plugin signals idempotently."""
    from menu_management.models import Menu, MenuItem
    from plugin_registry.models import PluginState

    page_published.connect(_on_wagtail_page_changed, dispatch_uid="cms_page_pub_sync")
    page_unpublished.connect(_on_wagtail_page_changed, dispatch_uid="cms_page_unpub_sync")

    for model, slug in ((MenuItem, "menuitem"), (Menu, "menu"), (PluginState, "pluginstate")):
        post_save.connect(
            _on_menu_or_plugin_changed,
            sender=model,
            dispatch_uid=f"cms_{slug}_save_cache_inv",
        )
        post_delete.connect(
            _on_menu_or_plugin_changed,
            sender=model,
            dispatch_uid=f"cms_{slug}_delete_cache_inv",
        )
