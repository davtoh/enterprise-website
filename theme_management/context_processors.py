from django.conf import settings
from .middleware import get_current_theme, AVAILABLE_THEMES


THEME_DISPLAY_NAMES = {
    'bootstrap5': 'Bootstrap 5.3',
    'tailwind': 'Tailwind CSS',
    'minimal': 'Minimal Semantic',
}

THEME_ICONS = {
    'bootstrap5': 'fa fa-bold',
    'tailwind': 'fa fa-wind',
    'minimal': 'fa fa-leaf',
}


def theme_context(request):
    """
    Exposes active theme and available themes for templates and CSS framework selectors.
    """
    current = getattr(request, 'site_theme', None) or get_current_theme()
    allowed = getattr(settings, 'AVAILABLE_THEMES', AVAILABLE_THEMES)

    choices = [
        {
            'name': code,
            'label': THEME_DISPLAY_NAMES.get(code, code.title()),
            'icon': THEME_ICONS.get(code, 'fa fa-paint-brush'),
            'is_active': (code == current),
        }
        for code in allowed
    ]

    return {
        'site_theme': current,
        'available_themes': allowed,
        'theme_choices': choices,
        'current_theme_label': THEME_DISPLAY_NAMES.get(current, current.title()),
        'current_theme_icon': THEME_ICONS.get(current, 'fa fa-paint-brush'),
    }
