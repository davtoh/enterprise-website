"""Split-settings renderers for `create_site` generated Django projects."""

from typing import Dict, List, Tuple

from plugin_registry.scaffolding.manifest import SiteManifest

_LANGUAGE_LABELS: Dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "pt": "Portuguese",
    "fr": "French",
    "it": "Italian",
    "ja": "Japanese",
}

_DJANGO_CORE_APPS: Tuple[str, ...] = (
    "daphne",
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.import_export",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
)

_THIRD_PARTY_APPS: Tuple[str, ...] = (
    "rest_framework",
    "drf_spectacular",
    "django_filters",
    "import_export",
    "django_htmx",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "django_countries",
    "phonenumber_field",
    "rosetta",
    "channels",
    "wagtail_localize",
    "wagtail_localize.locales",
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
)

_MIDDLEWARE_LINES: Tuple[str, ...] = (
    "    'django.middleware.security.SecurityMiddleware',",
    "    'django.contrib.sessions.middleware.SessionMiddleware',",
    "    'django.middleware.locale.LocaleMiddleware',",
    "    'django.middleware.common.CommonMiddleware',",
    "    'django.middleware.csrf.CsrfViewMiddleware',",
    "    'django.contrib.auth.middleware.AuthenticationMiddleware',",
    "    'django.contrib.messages.middleware.MessageMiddleware',",
    "    'django.middleware.clickjacking.XFrameOptionsMiddleware',",
    "    'django_htmx.middleware.HtmxMiddleware',",
    "    'allauth.account.middleware.AccountMiddleware',",
    "    'timezone_management.middleware.TimezoneMiddleware',",
    "    'theme_management.middleware.ThemeMiddleware',",
    "    'plugin_registry.middleware.PluginGatingMiddleware',",
    "    'wagtail.contrib.redirects.middleware.RedirectMiddleware',",
)


def _format_tuple_items(items: List[str], indent: int = 4) -> str:
    pad = " " * indent
    return "\n".join(f'{pad}"{item}",' for item in items)


def render_settings_init(manifest: SiteManifest) -> str:
    """Render `<project>/settings/__init__.py` importing split settings modules."""
    pkg = manifest.project_name
    return (
        f'"""Modular Django settings package for {pkg}."""\n\n'
        f"from {pkg}.settings.base import *  # noqa: F401,F403\n"
        f"from {pkg}.settings.apps import *  # noqa: F401,F403\n"
        f"from {pkg}.settings.storage import *  # noqa: F401,F403\n"
        f"from {pkg}.settings.security import *  # noqa: F401,F403\n"
        f"from {pkg}.settings.integrations import *  # noqa: F401,F403\n"
        f"from {pkg}.settings.unfold_config import *  # noqa: F401,F403\n"
    )


def render_settings_apps(manifest: SiteManifest) -> str:
    """Render `<project>/settings/apps.py` with core, third-party, and selected apps."""
    core = _format_tuple_items(list(_DJANGO_CORE_APPS))
    third_party = _format_tuple_items(list(_THIRD_PARTY_APPS))
    enterprise = _format_tuple_items(manifest.resolved_enterprise_apps())
    return (
        f'"""Installed applications for {manifest.project_name}."""\n\n'
        f"DJANGO_CORE_APPS = [\n{core}\n]\n\n"
        f"THIRD_PARTY_APPS = [\n{third_party}\n]\n\n"
        f"ENTERPRISE_APPS = [\n{enterprise}\n]\n\n"
        "INSTALLED_APPS = DJANGO_CORE_APPS + THIRD_PARTY_APPS + ENTERPRISE_APPS\n"
    )


def _render_base_header(manifest: SiteManifest) -> str:
    pkg = manifest.project_name
    labs_default = "True" if manifest.enable_labs else "False"
    return (
        f'"""Base configuration for {pkg}."""\n\n'
        "import os\nfrom pathlib import Path\n\n"
        "from django.contrib.messages import constants as messages\n"
        "from django.core.management.utils import get_random_secret_key\n"
        "from django.utils.translation import gettext_noop\n"
        "from dotenv import load_dotenv\n\n"
        "BASE_DIR = Path(__file__).resolve().parent.parent.parent\n"
        "load_dotenv(BASE_DIR / '.env')\n\n"
        "SECRET_KEY = os.getenv('SECRET_KEY') or get_random_secret_key()\n"
        "DEBUG = os.getenv('DEBUG', 'True') == 'True'\n"
        "ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]\n\n"
        f"ROOT_URLCONF = '{pkg}.urls'\n"
        f"WSGI_APPLICATION = '{pkg}.wsgi.application'\n"
        f"ASGI_APPLICATION = '{pkg}.routing.application'\n"
        "SITE_ID = 1\nDEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'\n\n"
        f"SITE_THEME = os.getenv('SITE_THEME', '{manifest.theme}')\n"
        f"ENABLE_LABS_PLUGINS = os.getenv('ENABLE_LABS_PLUGINS', '{labs_default}') == 'True'\n"
        "AVAILABLE_THEMES = ['bootstrap5', 'tailwind', 'minimal']\n\n"
    )


def _render_base_templates_and_i18n(manifest: SiteManifest) -> str:
    lang_lines = "\n".join(
        f'    ("{code}", gettext_noop("{_LANGUAGE_LABELS.get(code, code.upper())}")),'
        for code in manifest.languages
    )
    return (
        "TEMPLATES = [{\n"
        "    'BACKEND': 'django.template.backends.django.DjangoTemplates',\n"
        "    'DIRS': [BASE_DIR / 'templates'],\n"
        "    'OPTIONS': {\n"
        "        'loaders': [\n"
        "            'theme_management.template_loaders.ThemeTemplateLoader',\n"
        "            'django.template.loaders.filesystem.Loader',\n"
        "            'django.template.loaders.app_directories.Loader',\n"
        "        ],\n"
        "        'context_processors': [\n"
        "            'django.template.context_processors.debug',\n"
        "            'django.template.context_processors.request',\n"
        "            'django.contrib.auth.context_processors.auth',\n"
        "            'django.contrib.messages.context_processors.messages',\n"
        "            'menu_management.context_processors.dynamic_menu',\n"
        "            'theme_management.context_processors.theme_context',\n"
        "        ],\n"
        "    },\n"
        "}]\n\n"
        "LANGUAGE_CODE = 'en-us'\nTIME_ZONE = os.getenv('TIME_ZONE', 'UTC')\n"
        "USE_I18N = True\nUSE_TZ = True\n"
        "MESSAGE_TAGS = {messages.ERROR: 'danger'}\n"
        f"LANGUAGES = [\n{lang_lines}\n]\n"
        "LOCALE_PATHS = [BASE_DIR / 'locale']\nROSETTA_MESSAGES_PER_PAGE = 50\n"
        f"WAGTAIL_SITE_NAME = {manifest.display_name!r}\n"
        "WAGTAILADMIN_BASE_URL = os.getenv('WAGTAILADMIN_BASE_URL', 'http://localhost:8000')\n"
        "WAGTAIL_I18N_ENABLED = True\nWAGTAIL_CONTENT_LANGUAGES = LANGUAGES\n"
        "WAGTAILSEARCH_BACKENDS = {'default': {'BACKEND': 'wagtail.search.backends.database'}}\n"
    )


def render_settings_base(manifest: SiteManifest) -> str:
    """Render `<project>/settings/base.py` with middleware, templates, i18n, and Wagtail."""
    mw = "\n".join(_MIDDLEWARE_LINES)
    return (
        _render_base_header(manifest)
        + f"MIDDLEWARE = [\n{mw}\n]\n\n"
        + _render_base_templates_and_i18n(manifest)
    )


def render_settings_storage(manifest: SiteManifest) -> str:
    """Render `<project>/settings/storage.py` for database, static, media, and channels."""
    pkg = manifest.project_name
    sqlite_default = "True" if manifest.database == "sqlite" else "False"
    engine = "django.db.backends.mysql" if manifest.database == "mysql" else "django.db.backends.postgresql"
    port = "3306" if manifest.database == "mysql" else "5432"
    return (
        f'"""Storage, database, and channels configuration for {pkg}."""\n\n'
        f"import os\nimport sys\nfrom {pkg}.settings.base import BASE_DIR\n\n"
        f"USE_SQLITE = os.getenv('USE_SQLITE', '{sqlite_default}') == 'True'\n"
        "if USE_SQLITE:\n"
        "    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}\n"
        "else:\n"
        "    DATABASES = {'default': {\n"
        f"        'ENGINE': os.getenv('DB_ENGINE', '{engine}'), 'NAME': os.getenv('DB_NAME', '{pkg}'),\n"
        "        'USER': os.getenv('DB_USER', ''), 'PASSWORD': os.getenv('DB_PASSWORD', ''),\n"
        f"        'HOST': os.getenv('DB_HOST', ''), 'PORT': os.getenv('DB_PORT', '{port}'),\n"
        "    }}\n\n"
        "STATIC_URL = '/static/'\nSTATIC_ROOT = BASE_DIR / 'staticfiles'\n"
        "STATICFILES_DIRS = [BASE_DIR / 'static']\n"
        "MEDIA_URL = os.getenv('MEDIA_URL', '/media-files/')\nMEDIA_ROOT = BASE_DIR / 'media'\n"
        "TESTING = 'pytest' in sys.modules or 'test' in sys.argv\n"
        "REDIS_URL = os.getenv('REDIS_URL', '')\n"
        "if REDIS_URL and not TESTING:\n"
        "    CHANNEL_LAYERS = {'default': {'BACKEND': 'channels_redis.core.RedisChannelLayer', 'CONFIG': {'hosts': [REDIS_URL]}}}\n"
        "else:\n"
        "    CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}\n"
    )


def render_settings_security(manifest: SiteManifest) -> str:
    """Render `<project>/settings/security.py` with auth and production hardening."""
    pkg = manifest.project_name
    return (
        f'"""Security and authentication configuration for {pkg}."""\n\n'
        f"import os\nfrom {pkg}.settings.base import DEBUG\n\n"
        "LOGIN_REDIRECT_URL = '/'\nLOGOUT_REDIRECT_URL = '/'\nLOGIN_URL = '/accounts/login'\n"
        "AUTH_USER_MODEL = 'user_management.SiteUser'\n"
        "AUTHENTICATION_BACKENDS = [\n"
        "    'django.contrib.auth.backends.ModelBackend',\n"
        "    'allauth.account.auth_backends.AuthenticationBackend',\n"
        "]\n"
        "AUTH_PASSWORD_VALIDATORS = [\n"
        "    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},\n"
        "    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},\n"
        "    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},\n"
        "    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},\n"
        "]\n"
        "X_FRAME_OPTIONS = 'SAMEORIGIN'\nSECURE_CONTENT_TYPE_NOSNIFF = True\n"
        "CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]\n"
        "if not DEBUG:\n"
        "    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True') == 'True'\n"
        "    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True') == 'True'\n"
        "    CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'True') == 'True'\n"
        "    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')\n"
    )


def render_settings_integrations(manifest: SiteManifest) -> str:
    """Render `<project>/settings/integrations.py` for DRF, Celery, and logging."""
    pkg = manifest.project_name
    beat_entries: List[str] = []
    if "crm" in manifest.plugins:
        beat_entries.append("    'process-email-sequences': {'task': 'crm.tasks.process_email_sequences', 'schedule': 300.0},")
    if "erp" in manifest.plugins:
        beat_entries.append("    'check-low-stock-alerts': {'task': 'erp.tasks.check_low_stock_alerts', 'schedule': 3600.0},")
    beat_block = "\n".join(beat_entries)
    return (
        f'"""Integrations configuration for {pkg}."""\n\n'
        f"import os\nimport sys\nfrom {pkg}.settings.storage import REDIS_URL\n\n"
        "EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'\n"
        "REST_FRAMEWORK = {\n"
        "    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'],\n"
        "    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',\n"
        "    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],\n"
        "    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',\n"
        "    'PAGE_SIZE': 10,\n"
        "}\n"
        "SPECTACULAR_SETTINGS = {\n"
        f"    'TITLE': {manifest.display_name!r} + ' API',\n"
        f"    'DESCRIPTION': {manifest.description!r}, 'VERSION': '1.0.0',\n"
        "}\n"
        "CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)\n"
        "CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)\n"
        "CELERY_TASK_ALWAYS_EAGER = os.getenv('CELERY_TASK_ALWAYS_EAGER', 'False') == 'True' or 'pytest' in sys.modules or 'test' in sys.argv\n"
        f"CELERY_BEAT_SCHEDULE = {{\n{beat_block}\n}}\n"
        "INTELLIGENT_TRACKER_SECRET_KEY = os.getenv('INTELLIGENT_TRACKER_SECRET_KEY', '')\n"
    )


def render_settings_unfold(manifest: SiteManifest) -> str:
    """Render `<project>/settings/unfold_config.py` pruned to enabled plugins."""
    groups: List[str] = [
        "            {'title': _('Platform'), 'collapsible': True, 'items': [\n"
        "                {'title': _('Plugin Marketplace'), 'icon': 'extension', 'link': reverse_lazy('admin_marketplace')},\n"
        "                {'title': _('Users'), 'icon': 'person', 'link': reverse_lazy('admin:user_management_siteuser_changelist')},\n"
        "            ]},"
    ]
    if "crm" in manifest.plugins:
        groups.append(
            "            {'title': _('CRM'), 'collapsible': True, 'items': [\n"
            "                {'title': _('Contacts'), 'icon': 'contacts', 'link': reverse_lazy('admin:crm_contact_changelist')},\n"
            "                {'title': _('Leads'), 'icon': 'trending_up', 'link': reverse_lazy('admin:crm_lead_changelist')},\n"
            "            ]},"
        )
    if "erp" in manifest.plugins:
        groups.append(
            "            {'title': _('ERP'), 'collapsible': True, 'items': [\n"
            "                {'title': _('Products'), 'icon': 'inventory_2', 'link': reverse_lazy('admin:erp_product_changelist')},\n"
            "                {'title': _('Invoices'), 'icon': 'receipt_long', 'link': reverse_lazy('admin:erp_invoice_changelist')},\n"
            "            ]},"
        )
    nav = "\n".join(groups)
    return (
        f'"""Django Unfold admin configuration for {manifest.project_name}."""\n\n'
        "from django.urls import reverse_lazy\nfrom django.utils.translation import gettext_lazy as _\n\n"
        "UNFOLD = {\n"
        f"    'SITE_TITLE': {manifest.display_name!r}, 'SITE_HEADER': {manifest.display_name!r},\n"
        "    'SITE_SUBHEADER': _('Enterprise Control Plane'),\n"
        f"    'SIDEBAR': {{'show_search': True, 'navigation': [\n{nav}\n    ]}},\n"
        "}\n"
    )
