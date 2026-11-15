import importlib
from importlib import metadata
import logging
from typing import Dict, List, Optional, Type

from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.db import OperationalError, ProgrammingError

from .base import AppPlugin, PluginZone

logger = logging.getLogger(__name__)

PLUGIN_STATE_CACHE_KEY = "plugin_registry:plugin_states"
ENTRY_POINT_GROUP = "enterprise_website.plugins"


def _discover_installed_apps(register_fn) -> None:
    """Load AppPlugin subclasses from `<app>.plugin` across INSTALLED_APPS."""
    for app_config in apps.get_app_configs():
        module_name = f"{app_config.name}.plugin"
        try:
            mod = importlib.import_module(module_name)
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, AppPlugin)
                    and attr is not AppPlugin
                ):
                    register_fn(attr)
        except ModuleNotFoundError:
            continue
        except Exception as exc:
            logger.warning("Error loading plugin from %s: %s", module_name, exc)


def _discover_entry_points(register_fn) -> None:
    """Load AppPlugin subclasses from `enterprise_website.plugins` Python entry points."""
    try:
        eps = metadata.entry_points(group=ENTRY_POINT_GROUP)
    except Exception as exc:
        logger.warning("Error querying entry points for %s: %s", ENTRY_POINT_GROUP, exc)
        return

    for ep in eps:
        try:
            loaded = ep.load()
            if (
                isinstance(loaded, type)
                and issubclass(loaded, AppPlugin)
                and loaded is not AppPlugin
            ):
                register_fn(loaded)
            else:
                logger.warning(
                    "Entry point %s (%s) did not return an AppPlugin subclass",
                    ep.name,
                    ep.value,
                )
        except Exception as exc:
            logger.warning("Error loading entry point plugin %s: %s", ep.name, exc)


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

    def _get_plugin_states(self) -> Dict[str, bool]:
        """Return cached {slug: is_enabled} map from PluginState, or empty dict if DB is unready."""
        cached = cache.get(PLUGIN_STATE_CACHE_KEY)
        if cached is not None:
            return cached
        try:
            from .models import PluginState

            states = dict(PluginState.objects.values_list("slug", "is_enabled"))
        except (OperationalError, ProgrammingError):
            return {}
        cache.set(PLUGIN_STATE_CACHE_KEY, states, timeout=300)
        return states

    def is_plugin_enabled(self, slug: str) -> bool:
        """Return True if the plugin slug is enabled (system/empty/unpersisted plugins default True)."""
        if not slug or slug == "system":
            return True
        self.autodiscover()
        plugin_cls = self._plugins.get(slug)
        if plugin_cls is not None and getattr(plugin_cls, "is_system", False):
            return True
        if (
            plugin_cls is not None
            and plugin_cls.get_zone() == PluginZone.LABS
            and not getattr(settings, "ENABLE_LABS_PLUGINS", False)
        ):
            return False
        return bool(self._get_plugin_states().get(slug, True))

    def get_enabled_plugins(self) -> Dict[str, Type[AppPlugin]]:
        """Return all discovered plugins that are currently enabled."""
        self.autodiscover()
        return {
            name: plugin_cls
            for name, plugin_cls in self._plugins.items()
            if self.is_plugin_enabled(name)
        }

    def get_all_tasks(self) -> Dict[str, list]:
        """Return registered Celery tasks for enabled plugins, indexed by plugin name."""
        return {
            name: plugin_cls.get_tasks()
            for name, plugin_cls in self.get_enabled_plugins().items()
            if plugin_cls.get_tasks()
        }

    def get_all_plugin_templates(self) -> Dict[str, Dict[str, str]]:
        """Return registered theme templates for enabled plugins, indexed by plugin name."""
        return {
            name: plugin_cls.get_plugin_templates()
            for name, plugin_cls in self.get_enabled_plugins().items()
            if plugin_cls.get_plugin_templates()
        }

    def get_all_stream_blocks(self) -> Dict[str, List]:
        """Return registered CMS stream blocks for enabled plugins, indexed by plugin name."""
        return {
            name: plugin_cls.get_stream_blocks()
            for name, plugin_cls in self.get_enabled_plugins().items()
            if plugin_cls.get_stream_blocks()
        }

    def get_all_api_urlpatterns(self) -> Dict[str, List]:
        """Return registered API URL patterns for enabled plugins, indexed by plugin name."""
        return {
            name: plugin_cls.get_api_urlpatterns()
            for name, plugin_cls in self.get_enabled_plugins().items()
            if plugin_cls.get_api_urlpatterns()
        }

    def autodiscover(self):
        """Scan INSTALLED_APPS and Python entry points for AppPlugin subclasses."""
        if self._discovered:
            return
        _discover_installed_apps(self.register)
        _discover_entry_points(self.register)
        self._discovered = True


# Global registry singleton
registry = PluginRegistry()
