from typing import Any, Dict, List

from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from .base import PluginZone
from .models import PluginState
from .registry import registry


def _serialize_plugin_card(slug: str, plugin_cls: type) -> Dict[str, Any]:
    """Build display metadata dictionary for a single AppPlugin card."""
    zone = plugin_cls.get_zone().value
    return {
        "slug": slug,
        "verbose_name": plugin_cls.verbose_name or slug.replace("_", " ").title(),
        "description": plugin_cls.description,
        "version": plugin_cls.version,
        "author": plugin_cls.author,
        "icon": plugin_cls.icon,
        "category": plugin_cls.category,
        "zone": zone,
        "is_system": bool(getattr(plugin_cls, "is_system", False)),
        "requires_staff": bool(getattr(plugin_cls, "requires_staff", False)),
        "requires_auth": bool(getattr(plugin_cls, "requires_auth", False)),
        "is_enabled": registry.is_plugin_enabled(slug),
        "url_prefix": plugin_cls.url_prefix,
        "tasks_count": len(plugin_cls.get_tasks()),
        "menu_count": len(plugin_cls.get_menu_items()),
    }


def _filter_plugin_cards(
    cards: List[Dict[str, Any]],
    zone_filter: str,
    category_filter: str,
) -> List[Dict[str, Any]]:
    """Filter serialized plugin cards by optional zone and category."""
    result = cards
    if zone_filter:
        result = [c for c in result if c["zone"] == zone_filter]
    if category_filter:
        result = [c for c in result if c["category"] == category_filter]
    return result


class PluginMarketplaceView(TemplateView):
    """Staff-only Module Marketplace for viewing and toggling AppPlugins."""

    template_name = "plugin_registry/admin_marketplace.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(admin.site.each_context(self.request))

        all_plugins = registry.get_all_plugins()
        all_cards = sorted(
            (_serialize_plugin_card(slug, cls) for slug, cls in all_plugins.items()),
            key=lambda c: (c["zone"], c["verbose_name"].lower()),
        )

        zone_filter = self.request.GET.get("zone", "").strip().lower()
        category_filter = self.request.GET.get("category", "").strip().lower()
        filtered_cards = _filter_plugin_cards(all_cards, zone_filter, category_filter)

        context.update(
            {
                "title": _("Module Marketplace"),
                "plugins": filtered_cards,
                "total_count": len(all_cards),
                "enabled_count": sum(1 for c in all_cards if c["is_enabled"]),
                "zones": [z.value for z in PluginZone],
                "categories": sorted({c["category"] for c in all_cards if c["category"]}),
                "active_zone": zone_filter,
                "active_category": category_filter,
            }
        )
        return context

    def post(self, request, *args: Any, **kwargs: Any):
        slug = request.POST.get("slug", "").strip()
        action = request.POST.get("action", "").strip().lower()
        plugin_cls = registry.get_plugin(slug)

        if plugin_cls is None:
            messages.error(request, _("Unknown plugin: %(slug)s") % {"slug": slug})
            return redirect(reverse("admin_marketplace"))

        if getattr(plugin_cls, "is_system", False) and action != "enable":
            messages.error(
                request,
                _("Core system plugin '%(name)s' cannot be disabled.")
                % {"name": plugin_cls.verbose_name or slug},
            )
            return redirect(reverse("admin_marketplace"))

        new_enabled = action == "enable"
        PluginState.objects.update_or_create(
            slug=slug,
            defaults={"is_enabled": new_enabled},
        )
        label = plugin_cls.verbose_name or slug
        if new_enabled:
            messages.success(request, _("Enabled plugin '%(name)s'.") % {"name": label})
        else:
            messages.warning(request, _("Disabled plugin '%(name)s'.") % {"name": label})
        return redirect(reverse("admin_marketplace"))
