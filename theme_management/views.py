from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpRequest, HttpResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from .middleware import AVAILABLE_THEMES, DEFAULT_THEME, set_current_theme


def set_theme(request: HttpRequest, theme_name: str = "") -> HttpResponse:
    """
    Switch active CSS framework / UI theme.
    Saves selection to session and persistent cookie, then redirects back to previous page.
    """
    allowed_themes = getattr(settings, 'AVAILABLE_THEMES', AVAILABLE_THEMES)

    if not theme_name:
        theme_name = request.POST.get('theme') or request.GET.get('theme', '')

    theme_name = theme_name.strip().lower()

    if theme_name not in allowed_themes:
        theme_name = DEFAULT_THEME

    # Store in session
    if hasattr(request, 'session'):
        request.session['site_theme'] = theme_name

    # Set in thread-local for current cycle
    set_current_theme(theme_name)

    # Determine safe redirect target
    next_url = request.POST.get('next') or request.GET.get('next') or request.META.get('HTTP_REFERER') or '/'
    if not url_has_allowed_host_and_scheme(url=next_url, allowed_hosts={request.get_host()}):
        next_url = '/'

    response = HttpResponseRedirect(next_url)
    response.set_cookie('site_theme', theme_name, max_age=365 * 24 * 3600, samesite='Lax')
    return response
