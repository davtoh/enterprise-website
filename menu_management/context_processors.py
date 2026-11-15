from typing import Any, Dict, List, Optional

from django.utils import translation

from plugin_registry import registry
from .cache import get_cached_menu_tree
from .models import Menu, MenuItem


def _sort_menu_nodes(nodes: List[Dict[str, Any]], level: int = 0) -> None:
    """Sort menu tree nodes in place by (order, id) and assign depth levels."""
    nodes.sort(key=lambda n: (n['item'].order, n['item'].id))
    for node in nodes:
        node['level'] = level
        if node['children']:
            _sort_menu_nodes(node['children'], level=level + 1)


def _build_menu_hierarchy(
    accessible_items: List[MenuItem],
    language_code: str | None = None,
) -> List[Dict[str, Any]]:
    """Group flat accessible MenuItems into a sorted 3-level nested tree."""
    item_dict: Dict[int, Dict[str, Any]] = {
        item.id: {
            'item': item,
            'title': item.get_resolved_title(language_code=language_code),
            'url': item.get_resolved_url(language_code=language_code),
            'url_name': item.url_name,
            'icon': item.icon,
            'level': 0,
            'children': [],
        }
        for item in accessible_items
    }
    root_items: List[Dict[str, Any]] = []
    for item in accessible_items:
        node = item_dict[item.id]
        if item.parent_id and item.parent_id in item_dict:
            item_dict[item.parent_id]['children'].append(node)
        else:
            root_items.append(node)
    _sort_menu_nodes(root_items, level=0)
    return root_items


def _build_uncached_menu_tree(
    menu_slug: str,
    user=None,
    language_code: str | None = None,
) -> List[Dict[str, Any]]:
    """Query active Menu items and build a filtered, localized hierarchy."""
    try:
        menu = Menu.objects.get(slug=menu_slug, is_active=True)
    except Menu.DoesNotExist:
        return []

    items = list(
        menu.items.filter(is_visible=True).select_related(
            'parent', 'wagtail_page', 'wagtail_page__locale'
        )
    )
    accessible_items = [
        item
        for item in items
        if registry.is_plugin_enabled(item.plugin_source) and item.is_accessible_by(user)
    ]
    return _build_menu_hierarchy(accessible_items, language_code=language_code)


def get_menu_tree(
    menu_slug: str = 'main_navbar',
    user=None,
    language_code: str | None = None,
) -> List[Dict[str, Any]]:
    """Return a cached nested list of menu items scoped by role and locale."""
    lang = language_code or translation.get_language() or 'en'
    return get_cached_menu_tree(
        menu_slug=menu_slug,
        user=user,
        language_code=lang,
        builder=lambda: _build_uncached_menu_tree(menu_slug, user=user, language_code=lang),
    )


def _node_matches_path(node: Dict[str, Any], request_path: str) -> bool:
    """Return True if node or any descendant URL matches the active request_path."""
    url = node.get('url') or ''
    if url not in ('', '#', '/'):
        if request_path == url or request_path.startswith(url.rstrip('/') + '/'):
            return True
    return any(_node_matches_path(child, request_path) for child in node.get('children', []))


def _extract_active_section_sidebar(
    menu_tree: List[Dict[str, Any]],
    request_path: str,
) -> Optional[Dict[str, Any]]:
    """Extract the active root section's child tree for 3rd-level sidebar rendering."""
    if not request_path:
        return None
    for root_node in menu_tree:
        if root_node.get('children') and _node_matches_path(root_node, request_path):
            return {
                'title': root_node['title'],
                'url': root_node['url'],
                'items': root_node['children'],
                'active_path': request_path,
            }
    return None


def dynamic_menu(request):
    """Django context processor providing `main_navigation` and `section_sidebar`."""
    user = getattr(request, 'user', None)
    language_code = getattr(request, 'LANGUAGE_CODE', None) or translation.get_language()
    main_navigation = get_menu_tree('main_navbar', user=user, language_code=language_code)
    request_path = getattr(request, 'path', '') or ''
    return {
        'main_navigation': main_navigation,
        'section_sidebar': _extract_active_section_sidebar(main_navigation, request_path),
    }
