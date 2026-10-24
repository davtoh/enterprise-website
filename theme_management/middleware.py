import threading
from typing import Optional
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

_theme_local = threading.local()

DEFAULT_THEME = 'bootstrap5'
AVAILABLE_THEMES = getattr(settings, 'AVAILABLE_THEMES', ['bootstrap5', 'tailwind', 'minimal'])


def get_current_theme() -> str:
    """Returns the currently active theme name for the active thread or settings fallback."""
    theme = getattr(_theme_local, 'site_theme', None)
    if theme and theme in getattr(settings, 'AVAILABLE_THEMES', AVAILABLE_THEMES):
        return theme
    return getattr(settings, 'SITE_THEME', DEFAULT_THEME)


def set_current_theme(theme: Optional[str]) -> None:
    """Sets the active theme in thread-local storage."""
    _theme_local.site_theme = theme


def clear_current_theme() -> None:
    """Clears the active theme from thread-local storage."""
    _theme_local.site_theme = None


class ThemeMiddleware(MiddlewareMixin):
    """
    Middleware that determines the active CSS framework / UI theme per request.
    Supports:
      1. Query param: ?theme=<name>
      2. User session: request.session['site_theme']
      3. Cookie: request.COOKIES['site_theme']
      4. Global setting: settings.SITE_THEME (default 'bootstrap5')
    """

    def process_request(self, request):
        allowed_themes = getattr(settings, 'AVAILABLE_THEMES', AVAILABLE_THEMES)
        theme = None
        set_cookie = False

        # 1. Query parameter override (e.g. ?theme=tailwind)
        query_theme = request.GET.get('theme')
        if query_theme and query_theme in allowed_themes:
            theme = query_theme
            set_cookie = True
            if hasattr(request, 'session'):
                request.session['site_theme'] = theme

        # 2. Session override
        if not theme and hasattr(request, 'session'):
            session_theme = request.session.get('site_theme')
            if session_theme in allowed_themes:
                theme = session_theme

        # 3. Cookie fallback
        if not theme:
            cookie_theme = request.COOKIES.get('site_theme')
            if cookie_theme in allowed_themes:
                theme = cookie_theme

        # 4. Global settings fallback
        if not theme:
            theme = getattr(settings, 'SITE_THEME', DEFAULT_THEME)

        if theme not in allowed_themes:
            theme = DEFAULT_THEME

        request.site_theme = theme
        request._theme_set_cookie = set_cookie
        set_current_theme(theme)

    def process_response(self, request, response):
        try:
            if getattr(request, '_theme_set_cookie', False):
                theme = getattr(request, 'site_theme', DEFAULT_THEME)
                response.set_cookie('site_theme', theme, max_age=365 * 24 * 3600, samesite='Lax')
        finally:
            clear_current_theme()
        return response
