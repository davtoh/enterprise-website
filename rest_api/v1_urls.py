"""Unified /api/v1/ URL configuration with OpenAPI 3 schema, Swagger UI, Redoc, and plugin APIs."""

from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from plugin_registry.registry import get_active_api_urlpatterns

urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("", include("intelligent_tracker_hub.api_urls")),
    *get_active_api_urlpatterns(),
]
