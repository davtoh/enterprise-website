"""Project scaffolding generator engine for `create_site`."""

from pathlib import Path
import shutil
import subprocess
import sys
from typing import Iterable, Optional, Union

from django.conf import settings

from plugin_registry.scaffolding.manifest import CORE_ALWAYS_ON_APPS, SiteManifest
from plugin_registry.scaffolding.renderers import render_all_configs

_IGNORE_PATTERNS = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".DS_Store")

_SHARED_DIRS = ("templates", "static", "requirements", "locale")
_SHARED_FILES = ("manage.py", "utils.py", "pytest.ini", ".gitignore")
_DOCKER_FILES = ("Dockerfile", "docker-entrypoint.sh", "docker-compose.override.yml.example", ".dockerignore")


def _write_utf8(path: Path, content: str) -> None:
    """Write text as UTF-8 bytes to prevent Windows CRLF double-newline corruption."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))


def _copy_tree(src: Path, dst: Path) -> None:
    """Recursively copy a directory if it exists, skipping Python bytecode caches."""
    if not src.exists():
        return
    shutil.copytree(src, dst, ignore=_IGNORE_PATTERNS, dirs_exist_ok=True)


def _rewrite_package_ref(path: Path, new_pkg: str) -> None:
    """Replace `enterprise_website` package references in a copied Python/config file."""
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    updated = text.replace("enterprise_website", new_pkg)
    _write_utf8(path, updated)


class ProjectGenerator:
    """Materialize a standalone Django project from a validated SiteManifest."""

    def __init__(self, manifest: SiteManifest, source_root: Optional[Path] = None) -> None:
        self.manifest = manifest
        self.manifest.validate()
        self.source_root = Path(source_root or settings.BASE_DIR).resolve()

    def _prepare_target(self, target_dir: Optional[Union[str, Path]], overwrite: bool) -> Path:
        raw_target = target_dir or self.manifest.target_dir or (Path.cwd() / self.manifest.project_name)
        dest = Path(raw_target).resolve()
        if dest.exists() and any(dest.iterdir()) and not overwrite:
            raise FileExistsError(
                f"Target directory '{dest}' already exists and is not empty. Pass overwrite=True to replace."
            )
        dest.mkdir(parents=True, exist_ok=True)
        return dest

    def _copy_project_package(self, dest: Path) -> None:
        src_pkg = self.source_root / "enterprise_website"
        dst_pkg = dest / self.manifest.project_name
        dst_pkg.mkdir(parents=True, exist_ok=True)
        for item in src_pkg.iterdir():
            if item.name in ("__pycache__", "settings", "urls.py", "routing.py"):
                continue
            target_item = dst_pkg / item.name
            if item.is_dir():
                _copy_tree(item, target_item)
            else:
                shutil.copy2(item, target_item)
        for filename in ("wsgi.py", "asgi.py", "celery.py"):
            _rewrite_package_ref(dst_pkg / filename, self.manifest.project_name)

    def _copy_apps_and_assets(self, dest: Path) -> None:
        app_names: Iterable[str] = (*CORE_ALWAYS_ON_APPS, *self.manifest.plugins)
        for app_name in app_names:
            _copy_tree(self.source_root / app_name, dest / app_name)
        for dir_name in _SHARED_DIRS:
            _copy_tree(self.source_root / dir_name, dest / dir_name)
        for file_name in _SHARED_FILES:
            src_file = self.source_root / file_name
            if src_file.is_file():
                shutil.copy2(src_file, dest / file_name)
        _rewrite_package_ref(dest / "manage.py", self.manifest.project_name)
        _rewrite_package_ref(dest / "pytest.ini", self.manifest.project_name)

    def _copy_docker_assets(self, dest: Path) -> None:
        if not self.manifest.include_docker:
            return
        for file_name in _DOCKER_FILES:
            src_file = self.source_root / file_name
            if src_file.is_file():
                shutil.copy2(src_file, dest / file_name)
        _rewrite_package_ref(dest / "Dockerfile", self.manifest.project_name)
        _copy_tree(self.source_root / "nginx", dest / "nginx")

    def _write_rendered_files(self, dest: Path) -> None:
        for rel_path, content in render_all_configs(self.manifest).items():
            _write_utf8(dest / rel_path, content)
        self.manifest.write_json_file(dest / "site_manifest.json")

    def _run_i18n_bootstrap(self, dest: Path) -> None:
        subprocess.run(
            [sys.executable, "manage.py", "compilemessages"],
            cwd=str(dest),
            capture_output=True,
            text=True,
            check=False,
        )

    def generate(
        self,
        target_dir: Optional[Union[str, Path]] = None,
        overwrite: bool = False,
        run_i18n: bool = False,
    ) -> Path:
        """Generate the standalone project directory and return its resolved Path."""
        dest = self._prepare_target(target_dir, overwrite=overwrite)
        self._copy_project_package(dest)
        self._copy_apps_and_assets(dest)
        self._copy_docker_assets(dest)
        self._write_rendered_files(dest)
        if run_i18n:
            self._run_i18n_bootstrap(dest)
        return dest
