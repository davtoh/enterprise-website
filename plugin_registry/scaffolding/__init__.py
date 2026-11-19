"""Composable scaffolding engine for `manage.py create_site`."""

from .ai_advisor import suggest_manifest_from_prompt
from .cli_runner import (
    ConsoleWriter,
    add_scaffolding_arguments,
    execute_scaffolding,
    resolve_manifest_from_options,
)
from .generator import ProjectGenerator
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
from .renderers import render_all_configs

__all__ = [
    "CORE_ALWAYS_ON_APPS",
    "OPTIONAL_PLUGIN_APPS",
    "ProjectGenerator",
    "SUPPORTED_DATABASES",
    "SUPPORTED_LANGUAGES",
    "SUPPORTED_THEMES",
    "SiteManifest",
    "render_all_configs",
    "resolve_enterprise_app_configs",
    "resolve_plugin_dependencies",
    "suggest_manifest_from_prompt",
    "validate_project_identifier",
]
