"""Composable scaffolding engine for `manage.py create_site`."""

from .ai_advisor import suggest_manifest_from_prompt
from .manifest import (
    CORE_ALWAYS_ON_APPS,
    OPTIONAL_PLUGIN_APPS,
    SUPPORTED_DATABASES,
    SUPPORTED_LANGUAGES,
    SUPPORTED_THEMES,
    SiteManifest,
    resolve_enterprise_app_configs,
    resolve_plugin_dependencies,
    validate_project_identifier,
)

__all__ = [
    "CORE_ALWAYS_ON_APPS",
    "OPTIONAL_PLUGIN_APPS",
    "SUPPORTED_DATABASES",
    "SUPPORTED_LANGUAGES",
    "SUPPORTED_THEMES",
    "SiteManifest",
    "resolve_enterprise_app_configs",
    "resolve_plugin_dependencies",
    "suggest_manifest_from_prompt",
    "validate_project_identifier",
]
