from django.http import Http404
from django.utils.translation import gettext as _

from .registry import registry


def _strip_language_prefix(path: str, request) -> str:
    """Strip active LocaleMiddleware language prefix from a leading-slash-free path."""
    lang_code = getattr(request, "LANGUAGE_CODE", "") or ""
    if lang_code and (path == lang_code or path.startswith(f"{lang_code}/")):
        return path[len(lang_code):].lstrip("/")
    return path


def _matches_prefix(path: str, prefix: str) -> bool:
    """Return True when path equals prefix or starts with '<prefix>/'."""
    return path == prefix or path.startswith(f"{prefix}/")


class PluginGatingMiddleware:
    """Return HTTP 404 when a request targets a disabled plugin's url_prefix."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        raw_path = (getattr(request, "path_info", "") or "").lstrip("/")
        if raw_path:
            stripped_path = _strip_language_prefix(raw_path, request)
            for slug, plugin_cls in registry.get_all_plugins().items():
                if getattr(plugin_cls, "is_system", False):
                    continue
                prefix = (getattr(plugin_cls, "url_prefix", "") or "").strip("/")
                if not prefix:
                    continue
                if _matches_prefix(raw_path, prefix) or _matches_prefix(stripped_path, prefix):
                    if not registry.is_plugin_enabled(slug):
                        raise Http404(_("Plugin '%(name)s' is currently disabled.") % {"name": slug})
        return self.get_response(request)
