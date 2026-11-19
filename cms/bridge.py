import logging
from typing import Optional, Set

from django.db import transaction

from menu_management.cache import invalidate_menu_cache
from menu_management.models import Menu, MenuItem

logger = logging.getLogger(__name__)


def _upsert_wagtail_menu_item(
    menu: Menu,
    page,
    parent_item: Optional[MenuItem],
    order: int,
) -> MenuItem:
    """Create or update a non-custom MenuItem linked to a Wagtail Page."""
    page_url = page.url or ""
    existing = MenuItem.objects.filter(menu=menu, wagtail_page=page).first()
    if existing:
        if not existing.is_custom:
            updates = {
                "parent": parent_item,
                "title": page.title[:100],
                "url_path": page_url[:255],
                "order": order,
                "is_visible": True,
                "plugin_source": "cms",
            }
            if any(getattr(existing, field) != value for field, value in updates.items()):
                for field, value in updates.items():
                    setattr(existing, field, value)
                existing.save()
        return existing

    return MenuItem.objects.create(
        menu=menu,
        parent=parent_item,
        title=page.title[:100],
        url_name="",
        url_path=page_url[:255],
        order=order,
        is_visible=True,
        plugin_source="cms",
        is_custom=False,
        wagtail_page=page,
    )


def _sync_page_subtree(
    menu: Menu,
    parent_page,
    parent_item: Optional[MenuItem],
    depth: int,
    max_depth: int,
    synced_ids: Set[int],
) -> None:
    """Recursively sync live show_in_menus Wagtail pages up to max_depth."""
    if depth > max_depth:
        return
    children = parent_page.get_children().live().filter(show_in_menus=True).order_by("path")
    for idx, child_page in enumerate(children, start=1):
        menu_item = _upsert_wagtail_menu_item(menu, child_page, parent_item, idx * 10)
        synced_ids.add(child_page.id)
        _sync_page_subtree(menu, child_page, menu_item, depth + 1, max_depth, synced_ids)


def _prune_stale_wagtail_items(menu: Menu, synced_ids: Set[int]) -> int:
    """Remove auto-synced CMS MenuItems whose Wagtail pages are no longer live or visible."""
    stale_qs = MenuItem.objects.filter(
        menu=menu,
        plugin_source="cms",
        is_custom=False,
        wagtail_page__isnull=False,
    ).exclude(wagtail_page_id__in=synced_ids)
    deleted_count, _ = stale_qs.delete()
    return deleted_count


def sync_wagtail_menus(menu_slug: str = "main_navbar", max_depth: int = 3) -> int:
    """Idempotently sync the default Site's 3-level Wagtail page tree into MenuItem."""
    from wagtail.models import Site

    site = Site.objects.filter(is_default_site=True).first()
    if site is None or site.root_page_id is None:
        return 0

    with transaction.atomic():
        menu, _ = Menu.objects.get_or_create(
            slug=menu_slug,
            defaults={"title": "Main Navigation", "is_active": True},
        )
        synced_ids: Set[int] = set()
        _sync_page_subtree(menu, site.root_page, None, 1, max_depth, synced_ids)
        _prune_stale_wagtail_items(menu, synced_ids)

    invalidate_menu_cache()
    logger.info("Synced %d Wagtail pages into menu '%s'", len(synced_ids), menu_slug)
    return len(synced_ids)
