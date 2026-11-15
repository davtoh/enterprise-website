import hashlib
from typing import Any, Callable, Dict, List

from django.core.cache import cache
from django.utils import translation

MENU_CACHE_VERSION_KEY = "menu_management:cache_version"
MENU_CACHE_TIMEOUT = 300


def get_menu_cache_version() -> int:
    """Return the current version integer used to namespace menu cache keys."""
    version = cache.get(MENU_CACHE_VERSION_KEY)
    if version is None:
        version = 1
        cache.set(MENU_CACHE_VERSION_KEY, version, timeout=None)
    return int(version)


def invalidate_menu_cache() -> int:
    """Bump the menu cache version so all per-role/locale keys miss cleanly."""
    try:
        return int(cache.incr(MENU_CACHE_VERSION_KEY))
    except ValueError:
        next_version = get_menu_cache_version() + 1
        cache.set(MENU_CACHE_VERSION_KEY, next_version, timeout=None)
        return next_version


def get_user_role_key(user) -> str:
    """Map a user object to a coarse cache role bucket: anon, auth, or staff."""
    if not user or not getattr(user, "is_authenticated", False):
        return "anon"
    if getattr(user, "is_staff", False):
        return "staff"
    return "auth"


def get_enabled_plugins_signature() -> str:
    """Return a deterministic short hash of currently enabled plugin slugs."""
    from plugin_registry import registry

    registry.autodiscover()
    enabled = sorted(
        slug for slug in registry.get_all_plugins() if registry.is_plugin_enabled(slug)
    )
    payload = ",".join(enabled).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


def build_menu_cache_key(
    menu_slug: str,
    user=None,
    language_code: str | None = None,
) -> str:
    """Build a versioned cache key scoped by menu, role, locale, and plugin state."""
    version = get_menu_cache_version()
    role = get_user_role_key(user)
    lang = language_code or translation.get_language() or "en"
    plugins_sig = get_enabled_plugins_signature()
    return f"menu_tree:v{version}:{menu_slug}:{role}:{lang}:{plugins_sig}"


def get_cached_menu_tree(
    menu_slug: str,
    user=None,
    language_code: str | None = None,
    builder: Callable[[], List[Dict[str, Any]]] | None = None,
) -> List[Dict[str, Any]]:
    """Fetch a menu tree from cache or compute, store, and return it via builder."""
    key = build_menu_cache_key(menu_slug, user=user, language_code=language_code)
    cached = cache.get(key)
    if cached is not None:
        return cached
    if builder is None:
        return []
    tree = builder()
    cache.set(key, tree, timeout=MENU_CACHE_TIMEOUT)
    return tree
