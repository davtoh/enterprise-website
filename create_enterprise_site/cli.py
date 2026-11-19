"""Standalone `create-enterprise-site` CLI entrypoint."""

import argparse
import sys
from typing import Optional, Sequence, TextIO

from plugin_registry.scaffolding.cli_runner import (
    add_scaffolding_arguments,
    execute_scaffolding,
)

from . import __version__
from .fetcher import TemplateFetchError, resolve_template_source


def add_template_arguments(parser: argparse.ArgumentParser) -> None:
    """Register template acquisition flags on the standalone CLI parser."""
    group = parser.add_argument_group("Template Source Options")
    group.add_argument(
        "--template-dir",
        default=None,
        help="Path to a local enterprise_website repository or template directory.",
    )
    group.add_argument(
        "--template-url",
        default=None,
        help="HTTPS URL to a .zip or .tar.gz enterprise_website template archive.",
    )
    group.add_argument(
        "--template-sha256",
        default=None,
        help="Expected SHA-256 hex digest for --template-url archive verification.",
    )
    group.add_argument(
        "--git-url",
        default=None,
        help="Git repository URL (https://, ssh://, or git@...) for shallow template clone.",
    )
    group.add_argument(
        "--branch",
        default=None,
        help="Git branch or tag to clone when using --git-url (default: main).",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for `create-enterprise-site`."""
    parser = argparse.ArgumentParser(
        prog="create-enterprise-site",
        description="Scaffold a standalone composable enterprise Django & Wagtail site.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    add_template_arguments(parser)
    add_scaffolding_arguments(parser)
    return parser


def main(
    argv: Optional[Sequence[str]] = None,
    stdout: Optional[TextIO] = None,
    stderr: Optional[TextIO] = None,
    stdin: Optional[TextIO] = None,
) -> int:
    """Run the standalone `create-enterprise-site` CLI and return a process exit code."""
    err_stream = stderr if stderr is not None else sys.stderr
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    options = vars(args)

    try:
        if options.get("dry_run"):
            execute_scaffolding(options, stdout=stdout, stdin=stdin, source_root=None)
            return 0

        with resolve_template_source(
            template_dir=options.get("template_dir"),
            template_url=options.get("template_url"),
            template_sha256=options.get("template_sha256"),
            git_url=options.get("git_url"),
            branch=options.get("branch"),
        ) as source_root:
            execute_scaffolding(options, stdout=stdout, stdin=stdin, source_root=source_root)
        return 0
    except (TemplateFetchError, FileExistsError, ValueError, OSError) as exc:
        err_stream.write(f"Error: {exc}\n")
        return 1
    except KeyboardInterrupt:
        err_stream.write("\nAborted.\n")
        return 130
