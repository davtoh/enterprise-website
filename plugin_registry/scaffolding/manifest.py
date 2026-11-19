"""Declarative SiteManifest schema, validation, and plugin dependency resolver."""

from dataclasses import asdict, dataclass, field
import json
import keyword
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Set, Tuple, Union

from django.apps import apps

from plugin_registry.registry import registry

CORE_ALWAYS_ON_APPS: Tuple[str, ...] = (
    "plugin_registry",
    "menu_management",
    "home",
    "cms",
    "custom_tags",
    "user_management",
    "theme_management",
    "language_management",
    "timezone_management",
    "location_management",
)

OPTIONAL_PLUGIN_APPS: Tuple[str, ...] = (
    "todo",
    "polls",
    "webprogram",
    "rest_api",
    "task_runner",
    "video_gallery",
    "crm",
    "erp",
    "intelligent_tracker_hub",
)

SUPPORTED_THEMES: Tuple[str, ...] = ("bootstrap5", "tailwind", "minimal")
SUPPORTED_LANGUAGES: Tuple[str, ...] = ("en", "es", "pt", "fr", "it", "ja")
SUPPORTED_DATABASES: Tuple[str, ...] = ("sqlite", "postgres", "mysql")

PLUGIN_DEPENDENCY_MAP: Dict[str, Tuple[str, ...]] = {
    "erp": ("crm",),
    "intelligent_tracker_hub": ("crm", "video_gallery", "rest_api"),
}

ENTERPRISE_APP_CONFIG_ORDER: Tuple[Tuple[str, str], ...] = (
    ("plugin_registry", "plugin_registry.apps.PluginRegistryConfig"),
    ("menu_management", "menu_management.apps.MenuManagementConfig"),
    ("rest_api", "rest_api.apps.RestApiConfig"),
    ("webprogram", "webprogram.apps.WebprogramConfig"),
    ("home", "home.apps.HomeConfig"),
    ("cms", "cms.apps.CmsConfig"),
    ("todo", "todo.apps.TodoConfig"),
    ("language_management", "language_management.apps.LanguageManagementConfig"),
    ("polls", "polls.apps.PollsConfig"),
    ("custom_tags", "custom_tags.apps.CustomTagsConfig"),
    ("location_management", "location_management.apps.LocationManagementConfig"),
    ("user_management", "user_management.apps.UserManagementConfig"),
    ("timezone_management", "timezone_management.apps.TimezoneManagementConfig"),
    ("task_runner", "task_runner.apps.TaskRunnerConfig"),
    ("theme_management", "theme_management.apps.ThemeManagementConfig"),
    ("video_gallery", "video_gallery.apps.VideoGalleryConfig"),
    ("crm", "crm.apps.CrmConfig"),
    ("erp", "erp.apps.ErpConfig"),
    ("intelligent_tracker_hub", "intelligent_tracker_hub.apps.IntelligentTrackerHubConfig"),
)

RESERVED_PROJECT_NAMES: frozenset[str] = frozenset(
    {
        "django",
        "site",
        "test",
        "tests",
        "sys",
        "os",
        "enterprise_website",
        "static",
        "media",
        "templates",
        "locale",
        "docs",
        "documentation",
    }
)

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_project_identifier(raw_name: str) -> str:
    """Normalize and validate a Python package name for the generated Django project."""
    normalized = str(raw_name or "").strip().lower().replace("-", "_")
    if not _IDENTIFIER_RE.match(normalized):
        raise ValueError(
            f"Invalid project_name {raw_name!r}: must start with a letter and use lowercase letters, digits, or underscores."
        )
    if keyword.iskeyword(normalized) or normalized in RESERVED_PROJECT_NAMES:
        raise ValueError(
            f"Invalid project_name {raw_name!r}: conflicts with a Python keyword or reserved package name."
        )
    return normalized


def normalize_languages(languages: Iterable[str]) -> List[str]:
    """Validate selected locale codes against SUPPORTED_LANGUAGES and always include 'en'."""
    cleaned: List[str] = []
    for raw_code in languages:
        code = str(raw_code or "").strip().lower()
        if not code:
            continue
        if code not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language {raw_code!r}; expected one of {SUPPORTED_LANGUAGES}."
            )
        if code not in cleaned:
            cleaned.append(code)
    if not cleaned:
        return ["en"]
    if "en" not in cleaned:
        cleaned.insert(0, "en")
    return cleaned


def _lookup_plugin_dependencies(slug: str) -> Tuple[str, ...]:
    """Return declared dependencies for an optional plugin from fallback map and AppPlugin registry."""
    deps: Set[str] = set(PLUGIN_DEPENDENCY_MAP.get(slug, ()))
    if apps.ready:
        plugin_cls = registry.get_plugin(slug)
        if plugin_cls is not None:
            deps.update(getattr(plugin_cls, "dependencies", ()) or ())
    return tuple(deps)


def resolve_plugin_dependencies(
    selected_plugins: Iterable[str],
    strict: bool = True,
) -> List[str]:
    """Compute transitive dependency closure for optional plugins in canonical order."""
    queue: List[str] = []
    for raw_slug in selected_plugins:
        slug = str(raw_slug or "").strip().lower()
        if not slug or slug in CORE_ALWAYS_ON_APPS:
            continue
        if slug not in OPTIONAL_PLUGIN_APPS:
            if strict:
                raise ValueError(f"Unknown optional plugin {raw_slug!r}.")
            continue
        if slug not in queue:
            queue.append(slug)

    resolved: Set[str] = set()
    while queue:
        current = queue.pop(0)
        if current in resolved:
            continue
        resolved.add(current)
        for dep in _lookup_plugin_dependencies(current):
            dep_slug = str(dep).strip().lower()
            if dep_slug in OPTIONAL_PLUGIN_APPS and dep_slug not in resolved:
                queue.append(dep_slug)

    return [slug for slug in OPTIONAL_PLUGIN_APPS if slug in resolved]


def resolve_enterprise_app_configs(selected_plugins: Iterable[str]) -> List[str]:
    """Return ordered Django AppConfig dotted paths for core + resolved optional plugins."""
    enabled_apps: Set[str] = set(CORE_ALWAYS_ON_APPS)
    enabled_apps.update(resolve_plugin_dependencies(selected_plugins, strict=False))
    return [
        app_config
        for app_name, app_config in ENTERPRISE_APP_CONFIG_ORDER
        if app_name in enabled_apps
    ]


@dataclass
class SiteManifest:
    """Serializable specification for generating a standalone enterprise Django project."""

    project_name: str
    display_name: str = ""
    description: str = "Enterprise Django starter platform."
    target_dir: str = ""
    theme: str = "bootstrap5"
    languages: List[str] = field(default_factory=lambda: ["en", "es"])
    plugins: List[str] = field(default_factory=lambda: list(OPTIONAL_PLUGIN_APPS))
    database: str = "sqlite"
    include_docker: bool = True
    enable_labs: bool = False
    homepage_headline: str = ""
    homepage_subheadline: str = ""

    def validate(self) -> None:
        """Validate and normalize all manifest fields and plugin dependencies."""
        self.project_name = validate_project_identifier(self.project_name)
        self.display_name = (
            self.display_name.strip()
            or self.project_name.replace("_", " ").title()
        )
        self.description = (self.description or "Enterprise Django starter platform.").strip()
        self.theme = str(self.theme or "").strip().lower()
        if self.theme not in SUPPORTED_THEMES:
            raise ValueError(f"Unsupported theme {self.theme!r}; expected one of {SUPPORTED_THEMES}.")

        self.database = str(self.database or "").strip().lower()
        if self.database not in SUPPORTED_DATABASES:
            raise ValueError(
                f"Unsupported database {self.database!r}; expected one of {SUPPORTED_DATABASES}."
            )

        self.languages = normalize_languages(self.languages)
        self.plugins = resolve_plugin_dependencies(self.plugins, strict=True)
        self.include_docker = bool(self.include_docker)
        self.enable_labs = bool(self.enable_labs) or ("webprogram" in self.plugins)
        self.homepage_headline = self.homepage_headline.strip()
        self.homepage_subheadline = self.homepage_subheadline.strip()

    def resolved_enterprise_apps(self) -> List[str]:
        """Return ordered AppConfig paths for INSTALLED_APPS in the generated site."""
        return resolve_enterprise_app_configs(self.plugins)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize manifest into a JSON-safe dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize manifest into formatted JSON text."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SiteManifest":
        """Construct and validate a SiteManifest from a dictionary payload."""
        if not isinstance(data, dict) or not data.get("project_name"):
            raise ValueError("SiteManifest payload must be a mapping containing 'project_name'.")
        manifest = cls(
            project_name=data["project_name"],
            display_name=data.get("display_name", ""),
            description=data.get("description", "Enterprise Django starter platform."),
            target_dir=data.get("target_dir", ""),
            theme=data.get("theme", "bootstrap5"),
            languages=list(data.get("languages", ["en", "es"])),
            plugins=list(data.get("plugins", list(OPTIONAL_PLUGIN_APPS))),
            database=data.get("database", "sqlite"),
            include_docker=data.get("include_docker", True),
            enable_labs=data.get("enable_labs", False),
            homepage_headline=data.get("homepage_headline", ""),
            homepage_subheadline=data.get("homepage_subheadline", ""),
        )
        manifest.validate()
        return manifest

    @classmethod
    def from_json_file(cls, path: Union[Path, str]) -> "SiteManifest":
        """Load and validate a SiteManifest from a JSON file."""
        raw_text = Path(path).read_text(encoding="utf-8")
        return cls.from_dict(json.loads(raw_text))

    def write_json_file(self, path: Union[Path, str]) -> Path:
        """Write manifest JSON cleanly using UTF-8 LF binary writes."""
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes((self.to_json() + "\n").encode("utf-8"))
        return out_path
