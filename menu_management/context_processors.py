from typing import List, Dict, Any
from .models import Menu, MenuItem


def get_menu_tree(menu_slug: str = 'main_navbar', user=None) -> List[Dict[str, Any]]:
    """
    Returns a nested list of menu items for template rendering.
    Filters out hidden or unauthorized items.
    """
    try:
        menu = Menu.objects.get(slug=menu_slug, is_active=True)
    except Menu.DoesNotExist:
        return []

    # Fetch all items for this menu
    items = list(menu.items.filter(is_visible=True).select_related('parent'))

    # Filter by user permissions
    accessible_items = [item for item in items if item.is_accessible_by(user)]

    # Group into hierarchy
    item_dict: Dict[int, Dict[str, Any]] = {}
    for item in accessible_items:
        item_dict[item.id] = {
            'item': item,
            'title': item.title,
            'url': item.get_resolved_url(),
            'url_name': item.url_name,
            'icon': item.icon,
            'children': [],
        }

    root_items = []
    for item in accessible_items:
        node = item_dict[item.id]
        if item.parent_id and item.parent_id in item_dict:
            item_dict[item.parent_id]['children'].append(node)
        else:
            root_items.append(node)

    # Sort root and children by order
    def sort_nodes(nodes):
        nodes.sort(key=lambda n: (n['item'].order, n['item'].id))
        for n in nodes:
            if n['children']:
                sort_nodes(n['children'])

    sort_nodes(root_items)
    return root_items


def dynamic_menu(request):
    """
    Django context processor that makes `navigation_menu` available across all templates.
    """
    user = getattr(request, 'user', None)
    return {
        'main_navigation': get_menu_tree('main_navbar', user=user),
    }
