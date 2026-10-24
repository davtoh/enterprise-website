import os
from pathlib import Path
from typing import Generator
from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.template import Origin, TemplateDoesNotExist
from django.template.loaders.filesystem import Loader as FilesystemLoader
from django.utils._os import safe_join
from .middleware import get_current_theme


class ThemeTemplateLoader(FilesystemLoader):
    """
    Dynamic theme template loader that prioritizes theme-specific templates
    under `templates/themes/<current_theme>/` before falling back to default templates.
    Also supports AppPlugin `plugin_templates` mappings.
    """

    def get_template_sources(self, template_name: str) -> Generator[Origin, None, None]:
        current_theme = get_current_theme()
        theme_root = Path(settings.BASE_DIR) / 'templates' / 'themes' / current_theme

        # 1. Check plugin template mappings if registered (e.g. {'bootstrap5': 'todo/bs5/'})
        try:
            from plugin_registry import registry
            all_plugin_templates = registry.get_all_plugin_templates()
            for plugin_name, mapping in all_plugin_templates.items():
                if current_theme in mapping:
                    theme_prefix = mapping[current_theme].strip('/')
                    # If template_name starts with plugin_name, check mapped path
                    if template_name.startswith(f"{plugin_name}/"):
                        subpath = template_name[len(plugin_name) + 1:]
                        candidate_name = f"{theme_prefix}/{subpath}"
                        search_dirs = [theme_root, Path(settings.BASE_DIR) / 'templates']
                        try:
                            from django.apps import apps
                            for app_config in apps.get_app_configs():
                                app_dir = Path(app_config.path) / 'templates'
                                if app_dir.is_dir():
                                    search_dirs.append(app_dir)
                        except Exception:
                            pass

                        for search_dir in search_dirs:
                            try:
                                full_path = safe_join(str(search_dir), candidate_name)
                                yield Origin(
                                    name=full_path,
                                    template_name=template_name,
                                    loader=self,
                                )
                            except SuspiciousFileOperation:
                                pass
        except Exception:
            # Avoid breaking loader if registry is not ready yet
            pass

        # 2. Check theme-specific directory (templates/themes/<theme>/<template_name>)
        try:
            theme_path = safe_join(str(theme_root), template_name)
            yield Origin(
                name=theme_path,
                template_name=template_name,
                loader=self,
            )
        except SuspiciousFileOperation:
            pass

        # 3. Check base templates directory (templates/<template_name>)
        base_dir = Path(settings.BASE_DIR) / 'templates'
        try:
            base_path = safe_join(str(base_dir), template_name)
            yield Origin(
                name=base_path,
                template_name=template_name,
                loader=self,
            )
        except SuspiciousFileOperation:
            pass
