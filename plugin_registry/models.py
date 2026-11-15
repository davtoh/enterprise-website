from django.core.cache import cache
from django.db import models
from django.utils.translation import gettext_lazy as _

PLUGIN_STATE_CACHE_KEY = "plugin_registry:plugin_states"


def invalidate_plugin_state_cache() -> None:
    """Clear the cached plugin enabled-state map."""
    cache.delete(PLUGIN_STATE_CACHE_KEY)


class PluginState(models.Model):
    """Persisted runtime enable/disable state and JSON config for a plugin."""

    slug = models.SlugField(
        _("Slug"),
        max_length=100,
        unique=True,
        help_text=_("Unique plugin identifier matching AppPlugin.name."),
    )
    is_enabled = models.BooleanField(
        _("Enabled"),
        default=True,
        help_text=_("Whether this plugin's routes, menus, tasks, and blocks are active."),
    )
    config_json = models.JSONField(
        _("Configuration JSON"),
        default=dict,
        blank=True,
        help_text=_("Optional per-plugin runtime configuration."),
    )
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        verbose_name = _("Plugin State")
        verbose_name_plural = _("Plugin States")
        ordering = ["slug"]

    def __str__(self) -> str:
        status = _("enabled") if self.is_enabled else _("disabled")
        return f"{self.slug} ({status})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        invalidate_plugin_state_cache()

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        invalidate_plugin_state_cache()
        return result
