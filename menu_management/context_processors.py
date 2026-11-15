from typing import List, Dict, Any
from plugin_registry import registry
from .models import Menu, MenuItem


def _sort_menu_nodes(nodes: List[Dict[str, Any]]) -> None:
    """Sort menu tree nodes in place by (order, id)."""
    nodes.sort(key=lambda n: (n['item'].order, n['item'].id))
    for n in nodes:
        if n['children']:
            _sort_menu_nodes(n['children'])


def _build_menu_hierarchy(accessible_items: List[MenuItem]) -> List[Dict[str, Any]]:
    """Group flat accessible MenuItems into a sorted nested tree."""
    item_dict: Dict[int, Dict[str, Any]] = {
        item.id: {
            'item': item,
            'title': item.title,
            'url': item.get_resolved_url(),
            'url_name': item.url_name,
            'icon': item.icon,
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
    _sort_menu_nodes(root_items)
    return root_items


def get_menu_tree(menu_slug: str = 'main_navbar', user=None) -> List[Dict[str, Any]]:
    """
    Returns a nested list of menu items for template rendering.
    Filters out hidden, disabled-plugin, or unauthorized items.
    """
    try:
        menu = Menu.objects.get(slug=menu_slug, is_active=True)
    except Menu.DoesNotExist:
        return []

    items = list(menu.items.filter(is_visible=True).select_related('parent'))
    accessible_items = [
        item for item in items
        if registry.is_plugin_enabled(item.plugin_source) and item.is_accessible_by(user)
    ]
    return _build_menu_hierarchy(accessible_items)


def dynamic_menu(request):
    """
    Django context processor that makes `navigation_menu` available across all templates.
    """
    user = getattr(request, 'user', None)
    return {
        'main_navigation': get_menu_tree('main_navbar', user=user),
    }
