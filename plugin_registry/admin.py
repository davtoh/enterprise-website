from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import PluginState


@admin.register(PluginState)
class PluginStateAdmin(ModelAdmin):
    """Admin interface for persisted plugin enable/disable state and config."""

    list_display = ("slug", "is_enabled", "updated_at")
    list_filter = ("is_enabled",)
    search_fields = ("slug",)
    readonly_fields = ("updated_at",)
