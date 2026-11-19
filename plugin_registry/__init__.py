"""Plugin registry package with lazy exports for stdlib-only scaffolding imports."""

__all__ = ["AppPlugin", "MenuItemDefinition", "PluginZone", "registry"]


def __getattr__(name: str):
    if name in ("AppPlugin", "MenuItemDefinition", "PluginZone"):
        from .base import AppPlugin, MenuItemDefinition, PluginZone

        return {
            "AppPlugin": AppPlugin,
            "MenuItemDefinition": MenuItemDefinition,
            "PluginZone": PluginZone,
        }[name]
    if name == "registry":
        from .registry import registry

        return registry
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
