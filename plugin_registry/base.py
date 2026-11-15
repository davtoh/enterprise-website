from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class PluginZone(str, Enum):
    """Operational zone for an application plugin."""
    PUBLIC = "public"
    STAFF = "staff"
    LABS = "labs"


@dataclass
class MenuItemDefinition:
    """Definition of a navigation menu item exposed by a plugin."""
    label: str
    url_name: str = ""
    url_path: str = ""
    icon: str = ""
    order: int = 100
    parent_slug: Optional[str] = None
    requires_auth: bool = False
    requires_staff: bool = False
    permissions: List[str] = field(default_factory=list)


class AppPlugin:
    """
    Base class for all application plugins in Enterprise Website.
    Apps expose an AppPlugin subclass inside their `plugin.py` file.
    """
    name: str = ""  # Unique identifier, e.g. "todo"
    verbose_name: str = ""  # Human readable label, e.g. "Todo Task Manager"
    description: str = ""
    version: str = "1.0.0"
    author: str = "Enterprise Starter"
    icon: str = "fa-cubes"
    
    # URL and routing
    url_namespace: str = ""
    url_prefix: str = ""
    
    # Navigation menu items contributed by this plugin
    menu_items: List[MenuItemDefinition] = []
    
    # Feature / category grouping: "core", "productivity", "management", "utilities"
    category: str = "productivity"
    
    # Dependencies on other plugins (plugin names)
    dependencies: List[str] = []
    
    # Optional settings defaults required by this plugin
    settings_defaults: Dict[str, Any] = {}

    # Background Celery tasks registered by this plugin
    tasks: List[str] = []

    # Per-theme template directories / overrides: e.g. {'bootstrap5': 'todo/bs5/', 'tailwind': 'todo/tw/'}
    plugin_templates: Dict[str, str] = {}

    # AppPlugin v2 contract: zone, access policy, and modular extension points
    zone: PluginZone = PluginZone.PUBLIC
    requires_staff: bool = False
    requires_auth: bool = False
    is_system: bool = False
    stream_blocks: List[Any] = []
    api_urlpatterns: List[Any] = []
    dashboard_widgets: List[Dict[str, Any]] = []

    @classmethod
    def get_menu_items(cls) -> List[MenuItemDefinition]:
        return cls.menu_items

    @classmethod
    def get_tasks(cls) -> List[str]:
        return cls.tasks

    @classmethod
    def get_plugin_templates(cls) -> Dict[str, str]:
        return cls.plugin_templates

    @classmethod
    def get_zone(cls) -> PluginZone:
        return cls.zone if isinstance(cls.zone, PluginZone) else PluginZone(cls.zone)

    @classmethod
    def get_stream_blocks(cls) -> List[Any]:
        return cls.stream_blocks

    @classmethod
    def get_api_urlpatterns(cls) -> List[Any]:
        return cls.api_urlpatterns

    @classmethod
    def get_dashboard_widgets(cls) -> List[Dict[str, Any]]:
        return cls.dashboard_widgets
