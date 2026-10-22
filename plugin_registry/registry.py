import importlib
import logging
from typing import Dict, Type, Optional
from django.apps import apps
from .base import AppPlugin

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Central registry discovering and managing AppPlugins across installed apps."""

    def __init__(self):
        self._plugins: Dict[str, Type[AppPlugin]] = {}
        self._discovered: bool = False

    def register(self, plugin_cls: Type[AppPlugin]):
        """Register a plugin class."""
        if not issubclass(plugin_cls, AppPlugin):
            raise TypeError(f"{plugin_cls} must subclass AppPlugin")
        name = plugin_cls.name or plugin_cls.__name__.lower()
        self._plugins[name] = plugin_cls
        logger.debug("Registered AppPlugin: %s", name)

    def get_plugin(self, name: str) -> Optional[Type[AppPlugin]]:
        self.autodiscover()
        return self._plugins.get(name)

    def get_all_plugins(self) -> Dict[str, Type[AppPlugin]]:
        self.autodiscover()
        return dict(self._plugins)

    def autodiscover(self):
        """Scan all INSTALLED_APPS for a `plugin.py` module and load subclasses of AppPlugin."""
        if self._discovered:
            return

        for app_config in apps.get_app_configs():
            module_name = f"{app_config.name}.plugin"
            try:
                mod = importlib.import_module(module_name)
                # Find all AppPlugin classes defined in the module
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, AppPlugin)
                        and attr is not AppPlugin
                    ):
                        self.register(attr)
            except ModuleNotFoundError:
                # App does not declare a plugin.py, which is completely valid
                continue
            except Exception as e:
                logger.warning("Error loading plugin from %s: %s", module_name, e)

        self._discovered = True


# Global registry singleton
registry = PluginRegistry()
