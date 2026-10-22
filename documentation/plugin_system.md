# Plugin Registry & Dynamic Menus Architecture

This guide describes the plugin and dynamic navigation architecture introduced in **Milestone 8** of Enterprise Website.

---

## 1. Overview

Enterprise Website uses a decoupled **AppPlugin** pattern to allow modular applications (such as Todo, Polls, Brython, and future CRM/ERP modules) to declare themselves and contribute navigation links, routes, permissions, and settings to the host project automatically.

### Key Benefits
- **Zero-Coupling Navigation:** The navbar is no longer hardcoded in templates. Menus are dynamically resolved from installed plugins.
- **Admin Control & Overrides:** Site administrators can reorder menu items, change display titles, hide items, or add custom external links directly in the Django Admin (`/admin/menu_management/menu/`).
- **Permission & Auth-Aware:** Menu items can be conditionally visible only to authenticated users or staff members.
- **Scaffolding Ready:** The upcoming `python manage.py create_site` wizard will inspect registered plugins to let users toggle optional apps on or off.

---

## 2. Declaring an `AppPlugin`

Any Django app can register itself by creating a `plugin.py` file in its app directory subclassing `plugin_registry.AppPlugin`.

```python
# my_app/plugin.py
from plugin_registry import AppPlugin, MenuItemDefinition
from django.utils.translation import gettext_lazy as _

class MyAppPlugin(AppPlugin):
    name = "my_app"
    verbose_name = _("My Custom App")
    description = _("Description of what this app provides")
    icon = "fa fa-rocket"
    category = "productivity"  # e.g., 'core', 'productivity', 'management', 'utilities'
    
    menu_items = [
        MenuItemDefinition(
            label=_("My Dashboard"),
            url_name="my_app:index",
            icon="fa fa-tachometer",
            order=25,
            parent_slug="Apps",            # Nest under the "Apps" dropdown
            requires_auth=False,           # Restrict to logged-in users?
            requires_staff=False,          # Restrict to staff users?
        )
    ]
```

---

## 3. How Auto-Discovery Works

1. During Django application initialization (`PluginRegistryConfig.ready()`), `plugin_registry.registry.autodiscover()` scans all apps registered in `INSTALLED_APPS`.
2. Any subclass of `AppPlugin` inside `<app_name>.plugin` is registered into the singleton registry.
3. The `sync_menus` command (`python manage.py sync_menus`) synchronizes registered plugin menu items into the `Menu` and `MenuItem` database tables without overwriting manual administrator customizations.

---

## 4. Admin Management (`menu_management`)

Visit `/admin/menu_management/menu/` to:
- **Reorder links:** Edit the `order` number (lower numbers appear first).
- **Hide items:** Uncheck `is_visible` to hide a menu item without uninstalling the underlying app.
- **Add custom links:** Add links to external URLs or internal views.
- **Sync plugins:** Click the **"Sync discovered plugins into this menu"** action in the admin list to scan and add newly installed plugins.

---

## 5. Operations Commands

```powershell
# Synchronize all discovered plugins into the main navigation menu
.\.venv\Scripts\python.exe manage.py sync_menus

# Specify a custom menu slug if using secondary navigation (e.g. footer)
.\.venv\Scripts\python.exe manage.py sync_menus --menu footer
```
