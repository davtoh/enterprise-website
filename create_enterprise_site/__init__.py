"""Standalone `create-enterprise-site` CLI package for scaffolding enterprise Django sites."""

__version__ = "0.1.0"

from .fetcher import TemplateFetchError, is_valid_template_root, resolve_template_source

__all__ = [
    "TemplateFetchError",
    "__version__",
    "is_valid_template_root",
    "resolve_template_source",
]
