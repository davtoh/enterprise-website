"""Pure-stdlib CLI argument builder, interactive wizard, and runner for scaffolding."""

from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence, TextIO

from .ai_advisor import suggest_manifest_from_prompt
from .generator import ProjectGenerator
from .manifest import (
    OPTIONAL_PLUGIN_APPS,
    SUPPORTED_DATABASES,
    SUPPORTED_LANGUAGES,
    SUPPORTED_THEMES,
    SiteManifest,
)


class ConsoleWriter:
    """Adapter normalizing `write(msg, ending=...)` across Django OutputWrapper and TextIO."""

    def __init__(self, stream: Optional[TextIO] = None) -> None:
        self._stream: Any = stream if stream is not None else sys.stdout

    def write(self, msg: str = "", ending: str = "\n") -> None:
        """Write message with an explicit line ending."""
        self._stream.write(f"{msg}{ending}")

    def flush(self) -> None:
        """Flush underlying stream."""
        if hasattr(self._stream, "flush"):
            self._stream.flush()


def _as_writer(stdout: Any) -> Any:
    """Return a writer supporting `write(msg, ending=...)`."""
    if stdout is None:
        return ConsoleWriter(sys.stdout)
    if hasattr(stdout, "style_func"):
        return stdout
    return ConsoleWriter(stdout)


def parse_csv_list(raw_value: Any) -> List[str]:
    """Parse a comma-separated string or sequence into normalized lowercase tokens."""
    if raw_value is None:
        return []
    if isinstance(raw_value, (list, tuple, set)):
        items = [str(item).strip().lower() for item in raw_value]
    else:
        items = [part.strip().lower() for part in str(raw_value).split(",")]
    return [item for item in items if item]


def parse_plugins_value(raw_value: Any) -> List[str]:
    """Parse plugin selection supporting 'all', 'none', or comma-separated slugs."""
    tokens = parse_csv_list(raw_value)
    if not tokens or tokens == ["none"]:
        return []
    if tokens == ["all"]:
        return list(OPTIONAL_PLUGIN_APPS)
    return tokens


def add_scaffolding_arguments(parser: Any) -> None:
    """Register all shared `create_site` / `create-enterprise-site` CLI flags."""
    parser.add_argument("project_name", nargs="?", default=None, help="Python package name for the new project.")
    parser.add_argument("--display-name", default=None, help="Human-readable site title.")
    parser.add_argument("--description", default=None, help="Short site description.")
    parser.add_argument("--target-dir", default=None, help="Destination directory for the generated project.")
    parser.add_argument("--theme", choices=SUPPORTED_THEMES, default=None, help="Frontend CSS framework.")
    parser.add_argument("--languages", default=None, help="Comma-separated locale codes (e.g. en,es).")
    parser.add_argument("--plugins", default=None, help="Comma-separated optional plugins, 'all', or 'none'.")
    parser.add_argument("--database", choices=SUPPORTED_DATABASES, default=None, help="Database backend.")
    parser.add_argument("--docker", dest="include_docker", action="store_true", default=None, help="Include Docker files.")
    parser.add_argument("--no-docker", dest="include_docker", action="store_false", help="Omit Docker files.")
    parser.add_argument("--labs", dest="enable_labs", action="store_true", default=None, help="Enable Labs plugins.")
    parser.add_argument("--no-labs", dest="enable_labs", action="store_false", help="Disable Labs plugins.")
    parser.add_argument("--from-manifest", default=None, help="Load configuration from a JSON manifest file.")
    parser.add_argument("--dump-manifest", default=None, help="Write resolved SiteManifest JSON to this path.")
    parser.add_argument("--ai", nargs="?", const="", default=None, help="Use AI/heuristic advisor from a brief.")
    parser.add_argument("--no-input", "--noinput", dest="no_input", action="store_true", help="Skip interactive prompts.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite non-empty target directory.")
    parser.add_argument("--i18n", action="store_true", help="Run compilemessages in the generated project.")
    parser.add_argument("--dry-run", action="store_true", help="Validate/dump manifest without generating files.")


def _prompt_text(stdout: Any, label: str, default: str = "", stdin: Any = None) -> str:
    """Prompt stdin for a text value with an optional default."""
    suffix = f" [{default}]" if default else ""
    stdout.write(f"{label}{suffix}: ", ending="")
    stdout.flush()
    stream = stdin if stdin is not None else sys.stdin
    raw = stream.readline()
    if raw == "":
        return default
    cleaned = raw.strip()
    return cleaned if cleaned else default


def _prompt_choice(
    stdout: Any,
    label: str,
    choices: Sequence[str],
    default: str,
    stdin: Any = None,
) -> str:
    """Prompt stdin until the user enters a valid option from choices."""
    options_str = "/".join(choices)
    while True:
        answer = _prompt_text(stdout, f"{label} ({options_str})", default=default, stdin=stdin).lower()
        if answer in choices:
            return answer
        stdout.write(f"Invalid choice '{answer}'. Expected one of: {options_str}.")


def _prompt_bool(stdout: Any, label: str, default: bool = True, stdin: Any = None) -> bool:
    """Prompt stdin for a yes/no boolean answer."""
    default_token = "y" if default else "n"
    while True:
        answer = _prompt_text(stdout, f"{label} (y/n)", default=default_token, stdin=stdin).lower()
        if answer in ("y", "yes", "true", "1"):
            return True
        if answer in ("n", "no", "false", "0"):
            return False
        stdout.write("Please answer 'y' or 'n'.")


def build_base_manifest(options: Dict[str, Any]) -> SiteManifest:
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
        languages=parse_csv_list(options.get("languages")) or ["en", "es"],
        plugins=(
            parse_plugins_value(options["plugins"])
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


def apply_cli_overrides(manifest: SiteManifest, options: Dict[str, Any]) -> SiteManifest:
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
        manifest.languages = parse_csv_list(options["languages"])
    if options.get("plugins") is not None:
        manifest.plugins = parse_plugins_value(options["plugins"])
    if options.get("database"):
        manifest.database = options["database"]
    if options.get("include_docker") is not None:
        manifest.include_docker = bool(options["include_docker"])
    if options.get("enable_labs") is not None:
        manifest.enable_labs = bool(options["enable_labs"])
    manifest.validate()
    return manifest


def run_interactive_prompts(
    stdout: Any,
    manifest: SiteManifest,
    options: Dict[str, Any],
    stdin: Any = None,
) -> SiteManifest:
    """Collect missing or editable configuration interactively from stdin."""
    stdout.write("=== Enterprise Site Scaffolding Wizard ===")
    if not options.get("project_name"):
        manifest.project_name = _prompt_text(stdout, "Project package name", manifest.project_name, stdin=stdin)
    if not options.get("display_name"):
        default_display = manifest.display_name or manifest.project_name.replace("_", " ").title()
        manifest.display_name = _prompt_text(stdout, "Site display name", default_display, stdin=stdin)
    if not options.get("description"):
        manifest.description = _prompt_text(stdout, "Site description", manifest.description, stdin=stdin)
    if not options.get("target_dir"):
        default_dir = manifest.target_dir or str(Path.cwd() / manifest.project_name)
        manifest.target_dir = _prompt_text(stdout, "Target directory", default_dir, stdin=stdin)
    if not options.get("theme"):
        manifest.theme = _prompt_choice(stdout, "CSS theme", SUPPORTED_THEMES, manifest.theme, stdin=stdin)
    if options.get("languages") is None:
        lang_hint = "/".join(SUPPORTED_LANGUAGES)
        raw_langs = _prompt_text(stdout, f"Languages ({lang_hint})", ",".join(manifest.languages), stdin=stdin)
        manifest.languages = parse_csv_list(raw_langs) or ["en"]
    if options.get("plugins") is None:
        stdout.write(f"Available optional plugins: {', '.join(OPTIONAL_PLUGIN_APPS)}")
        default_plugins = ",".join(manifest.plugins) if manifest.plugins else "none"
        raw_plugins = _prompt_text(
            stdout, "Optional plugins (comma-separated, 'all', or 'none')", default_plugins, stdin=stdin
        )
        manifest.plugins = parse_plugins_value(raw_plugins)
    if not options.get("database"):
        manifest.database = _prompt_choice(stdout, "Database", SUPPORTED_DATABASES, manifest.database, stdin=stdin)
    if options.get("include_docker") is None:
        manifest.include_docker = _prompt_bool(stdout, "Include Docker support", manifest.include_docker, stdin=stdin)
    manifest.validate()
    return manifest


def resolve_manifest_from_options(
    stdout: Any,
    options: Dict[str, Any],
    stdin: Any = None,
) -> SiteManifest:
    """Resolve and validate a SiteManifest from CLI options and optional stdin prompts."""
    writer = _as_writer(stdout)
    manifest = build_base_manifest(options)
    if not options.get("no_input") and not options.get("from_manifest"):
        return run_interactive_prompts(writer, manifest, options, stdin=stdin)
    return apply_cli_overrides(manifest, options)


def print_next_steps(stdout: Any, dest: Path, manifest: SiteManifest) -> None:
    """Print post-generation Next Steps checklist."""
    writer = _as_writer(stdout)
    writer.write("")
    writer.write(f"Successfully scaffolded '{manifest.display_name}' at: {dest}")
    writer.write(f"Enabled plugins (with dependencies): {', '.join(manifest.plugins) or 'core-only'}")
    writer.write("")
    writer.write("Next Steps:")
    writer.write(f"  1. cd {dest}")
    writer.write("  2. cp .env.example .env  (set SECRET_KEY and DB/integration secrets)")
    writer.write("  3. python manage.py migrate")
    writer.write("  4. python manage.py createsuperuser")
    writer.write("  5. python manage.py runserver")


def execute_scaffolding(
    options: Dict[str, Any],
    stdout: Any = None,
    stdin: Any = None,
    source_root: Optional[Path] = None,
) -> Optional[Path]:
    """Run the full scaffolding flow (resolve -> dump -> dry-run -> generate -> next steps)."""
    writer = _as_writer(stdout)
    manifest = resolve_manifest_from_options(writer, options, stdin=stdin)

    dump_path = options.get("dump_manifest")
    if dump_path:
        written = manifest.write_json_file(dump_path)
        writer.write(f"Manifest written to: {written}")

    if options.get("dry_run"):
        writer.write("Dry run complete; no project files generated.")
        return None

    dest = ProjectGenerator(manifest, source_root=source_root).generate(
        target_dir=options.get("target_dir") or None,
        overwrite=bool(options.get("overwrite")),
        run_i18n=bool(options.get("i18n")),
    )
    print_next_steps(writer, dest, manifest)
    return dest
