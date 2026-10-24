from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


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

    @classmethod
    def get_menu_items(cls) -> List[MenuItemDefinition]:
        return cls.menu_items

    @classmethod
    def get_tasks(cls) -> List[str]:
        return cls.tasks
