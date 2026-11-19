"""URL, routing, environment, requirements, and Docker renderers for `create_site`."""

from typing import Dict, Tuple

from plugin_registry.scaffolding.manifest import SiteManifest
from plugin_registry.scaffolding.settings_renderers import (
    render_settings_apps,
    render_settings_base,
    render_settings_init,
    render_settings_integrations,
    render_settings_security,
    render_settings_storage,
    render_settings_unfold,
)

_OPTIONAL_URL_ROUTES: Tuple[Tuple[str, str, str], ...] = (
    ("todo", "todo/", "todo.urls"),
    ("polls", "polls/", "polls.urls"),
    ("webprogram", "webprogram/", "webprogram.urls"),
    ("task_runner", "tasks/", "task_runner.urls"),
    ("video_gallery", "media/", "video_gallery.urls"),
    ("crm", "crm/", "crm.urls"),
    ("erp", "erp/", "erp.urls"),
    ("intelligent_tracker_hub", "security/", "intelligent_tracker_hub.urls"),
    ("rest_api", "api/v1/", "rest_api.v1_urls"),
    ("rest_api", "rest_api/", "rest_api.urls"),
)

_CORE_URL_HEADER = (
    "from django.conf import settings\n"
    "from django.conf.urls.static import static\n"
    "from django.contrib import admin\n"
    "from django.urls import include, path\n"
    "from django.views.generic import RedirectView\n"
    "from wagtail import urls as wagtail_urls\n"
    "from wagtail.admin import urls as wagtailadmin_urls\n"
    "from wagtail.documents import urls as wagtaildocs_urls\n"
    "from language_management.views import set_language_and_sync_profile\n"
    "from plugin_registry.admin_views import PluginMarketplaceView\n"
    "from timezone_management import views as tz_views\n\n"
    "urlpatterns = [\n"
    "    path('', include('home.urls')),\n"
    "    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico', permanent=True)),\n"
    "    path('lang/', include('language_management.urls')),\n"
    "    path('tz/', include('timezone_management.urls')),\n"
    "    path('tz/set/', tz_views.set_timezone, name='set_timezone'),\n"
    "    path('accounts/', include('user_management.urls')),\n"
    "    path('theme/', include('theme_management.urls')),\n"
    "    path('admin/marketplace/', admin.site.admin_view(PluginMarketplaceView.as_view()), name='admin_marketplace'),\n"
    "    path('admin/', admin.site.urls),\n"
    "    path('cms/', include(wagtailadmin_urls)),\n"
    "    path('documents/', include(wagtaildocs_urls)),\n"
    "    path('i18n/setlang/', set_language_and_sync_profile, name='set_language'),\n"
    "    path('i18n/', include('django.conf.urls.i18n')),\n"
)


def render_urls_py(manifest: SiteManifest) -> str:
    """Render `<project>/urls.py` with core routes and enabled optional plugin routes."""
    enabled = set(manifest.plugins)
    optional_block = "\n".join(
        f"    path({route!r}, include({target!r})),"
        for slug, route, target in _OPTIONAL_URL_ROUTES
        if slug in enabled
    )
    return (
        f'"""URL configuration for {manifest.project_name}."""\n\n'
        + _CORE_URL_HEADER
        + f"{optional_block}\n]\n\n"
        + "if 'rosetta' in settings.INSTALLED_APPS:\n"
        + "    urlpatterns += [path('rosetta/', include('rosetta.urls'))]\n"
        + "if settings.DEBUG:\n"
        + "    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)\n"
        + "urlpatterns += [path('', include(wagtail_urls))]\n"
    )


def render_rest_api_v1_urls(manifest: SiteManifest) -> str:
    """Render `rest_api/v1_urls.py` without unconditional optional plugin imports."""
    tracker_line = (
        '    path("", include("intelligent_tracker_hub.api_urls")),\n'
        if "intelligent_tracker_hub" in manifest.plugins
        else ""
    )
    return (
        '"""Versioned REST API v1 routing."""\n\n'
        "from django.urls import include, path\n"
        "from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView\n"
        "from plugin_registry.registry import get_active_api_urlpatterns\n\n"
        "urlpatterns = [\n"
        '    path("schema/", SpectacularAPIView.as_view(), name="api-v1-schema"),\n'
        '    path("docs/", SpectacularSwaggerView.as_view(url_name="api-v1-schema"), name="api-v1-docs"),\n'
        '    path("redoc/", SpectacularRedocView.as_view(url_name="api-v1-schema"), name="api-v1-redoc"),\n'
        f"{tracker_line}"
        "    *get_active_api_urlpatterns(),\n"
        "]\n"
    )


def render_routing_py(manifest: SiteManifest) -> str:
    """Render `<project>/routing.py` guarding optional `task_runner` WebSockets."""
    ws_import = "import task_runner.routing\n" if "task_runner" in manifest.plugins else ""
    ws_patterns = "task_runner.routing.websocket_urlpatterns" if "task_runner" in manifest.plugins else "[]"
    return (
        "from django.core.asgi import get_asgi_application\n"
        "from channels.auth import AuthMiddlewareStack\n"
        "from channels.routing import ProtocolTypeRouter, URLRouter\n"
        f"{ws_import}\n"
        "django_asgi_app = get_asgi_application()\n\n"
        "application = ProtocolTypeRouter({\n"
        '    "http": django_asgi_app,\n'
        f'    "websocket": AuthMiddlewareStack(URLRouter({ws_patterns})),\n'
        "})\n"
    )


def render_env_example(manifest: SiteManifest) -> str:
    """Render `.env.example` tailored to the manifest database and plugins."""
    use_sqlite = "True" if manifest.database == "sqlite" else "False"
    labs_flag = "True" if manifest.enable_labs else "False"
    return (
        f"# Environment configuration for {manifest.display_name}\n"
        "DEBUG=True\nSECRET_KEY=replace-with-secure-random-key\n"
        "ALLOWED_HOSTS=localhost,127.0.0.1\n"
        f"SITE_THEME={manifest.theme}\nENABLE_LABS_PLUGINS={labs_flag}\n"
        f"USE_SQLITE={use_sqlite}\nDB_NAME={manifest.project_name}\n"
        "DB_USER=\nDB_PASSWORD=\nDB_HOST=\nDB_PORT=\n"
        "REDIS_URL=\nCELERY_TASK_ALWAYS_EAGER=True\n"
    )


def render_requirements_txt(manifest: SiteManifest) -> str:
    """Render `requirements.txt` referencing `requirements/base.txt` and DB drivers."""
    extra = ""
    if manifest.database == "postgres":
        extra = "\npsycopg2-binary>=2.9.9\n"
    elif manifest.database == "mysql":
        extra = "\nmysqlclient>=2.2.0\n"
    return f"-r requirements/base.txt{extra}"


def render_docker_compose(manifest: SiteManifest) -> str:
    """Render `docker-compose.yml` without exposing internal DB/Redis host ports."""
    pkg = manifest.project_name
    return (
        "services:\n  web:\n    build: .\n"
        f"    container_name: {pkg}_web\n"
        "    expose:\n      - '8000'\n    env_file:\n      - .env\n"
        "    depends_on:\n      - db\n      - redis\n"
        "  db:\n    image: postgres:16-alpine\n"
        f"    container_name: {pkg}_db\n    environment:\n      POSTGRES_DB: {pkg}\n"
        "      POSTGRES_USER: ${DB_USER:-postgres}\n      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}\n"
        "  redis:\n    image: redis:7-alpine\n"
        f"    container_name: {pkg}_redis\n"
        "  celery_worker:\n    build: .\n"
        f"    container_name: {pkg}_celery\n"
        f"    command: celery -A {pkg} worker -l INFO\n"
        "    env_file:\n      - .env\n    depends_on:\n      - redis\n"
    )


def render_all_configs(manifest: SiteManifest) -> Dict[str, str]:
    """Return a map of repo-relative file paths to rendered file contents."""
    pkg = manifest.project_name
    rendered: Dict[str, str] = {
        f"{pkg}/settings/__init__.py": render_settings_init(manifest),
        f"{pkg}/settings/apps.py": render_settings_apps(manifest),
        f"{pkg}/settings/base.py": render_settings_base(manifest),
        f"{pkg}/settings/storage.py": render_settings_storage(manifest),
        f"{pkg}/settings/security.py": render_settings_security(manifest),
        f"{pkg}/settings/integrations.py": render_settings_integrations(manifest),
        f"{pkg}/settings/unfold_config.py": render_settings_unfold(manifest),
        f"{pkg}/urls.py": render_urls_py(manifest),
        f"{pkg}/routing.py": render_routing_py(manifest),
        ".env.example": render_env_example(manifest),
        "requirements.txt": render_requirements_txt(manifest),
    }
    if "rest_api" in manifest.plugins:
        rendered["rest_api/v1_urls.py"] = render_rest_api_v1_urls(manifest)
    if manifest.include_docker:
        rendered["docker-compose.yml"] = render_docker_compose(manifest)
    return rendered
