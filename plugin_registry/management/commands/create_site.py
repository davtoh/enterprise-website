"""Interactive and non-interactive `manage.py create_site` scaffolding wizard."""

from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils.translation import gettext as _

from plugin_registry.scaffolding import (
    OPTIONAL_PLUGIN_APPS,
    ProjectGenerator,
    SUPPORTED_DATABASES,
    SUPPORTED_LANGUAGES,
    SUPPORTED_THEMES,
    SiteManifest,
    suggest_manifest_from_prompt,
)


def _parse_csv_list(raw_value: Any) -> List[str]:
    """Parse a comma-separated string or sequence into normalized lowercase tokens."""
    if raw_value is None:
        return []
    if isinstance(raw_value, (list, tuple, set)):
        items = [str(item).strip().lower() for item in raw_value]
    else:
        items = [part.strip().lower() for part in str(raw_value).split(",")]
    return [item for item in items if item]


def _parse_plugins_value(raw_value: Any) -> List[str]:
    """Parse plugin selection supporting 'all', 'none', or comma-separated slugs."""
    tokens = _parse_csv_list(raw_value)
    if not tokens or tokens == ["none"]:
        return []
    if tokens == ["all"]:
        return list(OPTIONAL_PLUGIN_APPS)
    return tokens


def _prompt_text(stdout: Any, label: str, default: str = "") -> str:
    """Prompt stdin for a text value with an optional default."""
    suffix = f" [{default}]" if default else ""
    stdout.write(f"{label}{suffix}: ", ending="")
    stdout.flush()
    raw = sys.stdin.readline()
    if raw == "":
        return default
    cleaned = raw.strip()
    return cleaned if cleaned else default


def _prompt_choice(
    stdout: Any,
    label: str,
    choices: Sequence[str],
    default: str,
) -> str:
    """Prompt stdin until the user enters a valid option from choices."""
    options_str = "/".join(choices)
    while True:
        answer = _prompt_text(stdout, f"{label} ({options_str})", default=default).lower()
        if answer in choices:
            return answer
        stdout.write(f"Invalid choice '{answer}'. Expected one of: {options_str}.")


def _prompt_bool(stdout: Any, label: str, default: bool = True) -> bool:
    """Prompt stdin for a yes/no boolean answer."""
    default_token = "y" if default else "n"
    while True:
        answer = _prompt_text(stdout, f"{label} (y/n)", default=default_token).lower()
        if answer in ("y", "yes", "true", "1"):
            return True
        if answer in ("n", "no", "false", "0"):
            return False
        stdout.write("Please answer 'y' or 'n'.")


def _build_base_manifest(options: Dict[str, Any]) -> SiteManifest:
    """Construct initial SiteManifest from --from-manifest, --ai, or CLI defaults."""
    from_manifest = options.get("from_manifest")
    if from_manifest:
        return SiteManifest.from_json_file(from_manifest)

    raw_name = options.get("project_name") or "enterprise_site"
    manifest = SiteManifest(
        project_name=raw_name,
        display_name=options.get("display_name") or "",
        description=options.get("description") or "Enterprise Django starter platform.",
        target_dir=options.get("target_dir") or "",
        theme=options.get("theme") or "bootstrap5",
        languages=_parse_csv_list(options.get("languages")) or ["en", "es"],
        plugins=(
            _parse_plugins_value(options["plugins"])
            if options.get("plugins") is not None
            else list(OPTIONAL_PLUGIN_APPS)
        ),
        database=options.get("database") or "sqlite",
        include_docker=(
            True if options.get("include_docker") is None else bool(options["include_docker"])
        ),
        enable_labs=bool(options.get("enable_labs") or False),
    )

    ai_prompt = options.get("ai")
    if ai_prompt is not None:
        brief = ai_prompt.strip() or manifest.description
        manifest = suggest_manifest_from_prompt(brief, base_manifest=manifest)
    return manifest


def _apply_cli_overrides(manifest: SiteManifest, options: Dict[str, Any]) -> SiteManifest:
    """Apply explicit CLI flag overrides on top of a loaded or AI-suggested manifest."""
    if options.get("project_name"):
        manifest.project_name = options["project_name"]
    if options.get("display_name"):
        manifest.display_name = options["display_name"]
    if options.get("description"):
        manifest.description = options["description"]
    if options.get("target_dir"):
        manifest.target_dir = options["target_dir"]
    if options.get("theme"):
        manifest.theme = options["theme"]
    if options.get("languages") is not None:
        manifest.languages = _parse_csv_list(options["languages"])
    if options.get("plugins") is not None:
        manifest.plugins = _parse_plugins_value(options["plugins"])
    if options.get("database"):
        manifest.database = options["database"]
    if options.get("include_docker") is not None:
        manifest.include_docker = bool(options["include_docker"])
    if options.get("enable_labs") is not None:
        manifest.enable_labs = bool(options["enable_labs"])
    manifest.validate()
    return manifest


def _run_interactive_prompts(stdout: Any, manifest: SiteManifest, options: Dict[str, Any]) -> SiteManifest:
    """Collect missing or editable configuration interactively from stdin."""
    stdout.write("=== Enterprise Site Scaffolding Wizard ===")
    if not options.get("project_name"):
        manifest.project_name = _prompt_text(stdout, "Project package name", manifest.project_name)
    if not options.get("display_name"):
        default_display = manifest.display_name or manifest.project_name.replace("_", " ").title()
        manifest.display_name = _prompt_text(stdout, "Site display name", default_display)
    if not options.get("description"):
        manifest.description = _prompt_text(stdout, "Site description", manifest.description)
    if not options.get("target_dir"):
        default_dir = manifest.target_dir or str(Path.cwd() / manifest.project_name)
        manifest.target_dir = _prompt_text(stdout, "Target directory", default_dir)
    if not options.get("theme"):
        manifest.theme = _prompt_choice(stdout, "CSS theme", SUPPORTED_THEMES, manifest.theme)
    if options.get("languages") is None:
        lang_hint = "/".join(SUPPORTED_LANGUAGES)
        raw_langs = _prompt_text(stdout, f"Languages ({lang_hint})", ",".join(manifest.languages))
        manifest.languages = _parse_csv_list(raw_langs) or ["en"]
    if options.get("plugins") is None:
        stdout.write(f"Available optional plugins: {', '.join(OPTIONAL_PLUGIN_APPS)}")
        default_plugins = ",".join(manifest.plugins) if manifest.plugins else "none"
        raw_plugins = _prompt_text(
            stdout, "Optional plugins (comma-separated, 'all', or 'none')", default_plugins
        )
        manifest.plugins = _parse_plugins_value(raw_plugins)
    if not options.get("database"):
        manifest.database = _prompt_choice(stdout, "Database", SUPPORTED_DATABASES, manifest.database)
    if options.get("include_docker") is None:
        manifest.include_docker = _prompt_bool(stdout, "Include Docker support", manifest.include_docker)
    manifest.validate()
    return manifest


def _print_next_steps(stdout: Any, dest: Path, manifest: SiteManifest) -> None:
    """Print post-generation Next Steps checklist."""
    stdout.write("")
    stdout.write(_(f"Successfully scaffolded '{manifest.display_name}' at: {dest}"))
    stdout.write(_(f"Enabled plugins (with dependencies): {', '.join(manifest.plugins) or 'core-only'}"))
    stdout.write("")
    stdout.write(_("Next Steps:"))
    stdout.write(f"  1. cd {dest}")
    stdout.write("  2. cp .env.example .env  (set SECRET_KEY and DB/integration secrets)")
    stdout.write("  3. python manage.py migrate")
    stdout.write("  4. python manage.py createsuperuser")
    stdout.write("  5. python manage.py runserver")


class Command(BaseCommand):
    """Scaffold a standalone composable Django site from this enterprise template."""

    help = _("Create a standalone composable Django project from a SiteManifest or interactive wizard.")

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("project_name", nargs="?", default=None, help=_("Python package name for the new project."))
        parser.add_argument("--display-name", default=None, help=_("Human-readable site title."))
        parser.add_argument("--description", default=None, help=_("Short site description."))
        parser.add_argument("--target-dir", default=None, help=_("Destination directory for the generated project."))
        parser.add_argument("--theme", choices=SUPPORTED_THEMES, default=None, help=_("Frontend CSS framework."))
        parser.add_argument("--languages", default=None, help=_("Comma-separated locale codes (e.g. en,es)."))
        parser.add_argument("--plugins", default=None, help=_("Comma-separated optional plugins, 'all', or 'none'."))
        parser.add_argument("--database", choices=SUPPORTED_DATABASES, default=None, help=_("Database backend."))
        parser.add_argument("--docker", dest="include_docker", action="store_true", default=None, help=_("Include Docker files."))
        parser.add_argument("--no-docker", dest="include_docker", action="store_false", help=_("Omit Docker files."))
        parser.add_argument("--labs", dest="enable_labs", action="store_true", default=None, help=_("Enable Labs plugins."))
        parser.add_argument("--no-labs", dest="enable_labs", action="store_false", help=_("Disable Labs plugins."))
        parser.add_argument("--from-manifest", default=None, help=_("Load configuration from a JSON manifest file."))
        parser.add_argument("--dump-manifest", default=None, help=_("Write resolved SiteManifest JSON to this path."))
        parser.add_argument("--ai", nargs="?", const="", default=None, help=_("Use AI/heuristic advisor from a brief."))
        parser.add_argument("--no-input", "--noinput", dest="no_input", action="store_true", help=_("Skip interactive prompts."))
        parser.add_argument("--overwrite", action="store_true", help=_("Overwrite non-empty target directory."))
        parser.add_argument("--i18n", action="store_true", help=_("Run compilemessages in the generated project."))
        parser.add_argument("--dry-run", action="store_true", help=_("Validate/dump manifest without generating files."))

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            manifest = _build_base_manifest(options)
            if not options.get("no_input") and not options.get("from_manifest"):
                manifest = _run_interactive_prompts(self.stdout, manifest, options)
            else:
                manifest = _apply_cli_overrides(manifest, options)
        except (ValueError, OSError) as exc:
            raise CommandError(str(exc)) from exc

        dump_path = options.get("dump_manifest")
        if dump_path:
            written = manifest.write_json_file(dump_path)
            self.stdout.write(_(f"Manifest written to: {written}"))

        if options.get("dry_run"):
            self.stdout.write(_("Dry run complete; no project files generated."))
            return

        try:
            dest = ProjectGenerator(manifest).generate(
                target_dir=options.get("target_dir") or None,
                overwrite=bool(options.get("overwrite")),
                run_i18n=bool(options.get("i18n")),
            )
        except (FileExistsError, ValueError, OSError) as exc:
            raise CommandError(str(exc)) from exc

        _print_next_steps(self.stdout, dest, manifest)
