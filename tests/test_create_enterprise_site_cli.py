"""Unit tests for stdlib scaffolding decoupling, shared cli_runner, and template fetcher."""

import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from unittest.mock import MagicMock, patch
import zipfile

import pytest

from create_enterprise_site.cli import main as cli_main
from create_enterprise_site.fetcher import (
    TemplateFetchError,
    is_valid_template_root,
    resolve_template_source,
)
from plugin_registry.scaffolding import SiteManifest
from plugin_registry.scaffolding.cli_runner import execute_scaffolding
from tests.test_create_site import _run_generated_manage

REPO_ROOT = Path(__file__).resolve().parents[1]


def _make_fake_template(root: Path) -> Path:
    """Create minimal marker structure recognized by `is_valid_template_root`."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "manage.py").write_bytes(b"#!/usr/bin/env python\n")
    (root / "enterprise_website").mkdir(exist_ok=True)
    (root / "plugin_registry").mkdir(exist_ok=True)
    return root


def _build_zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _build_tar_gz_bytes(entries: dict[str, bytes], symlink_name: str | None = None) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, data in entries.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
        if symlink_name:
            sym = tarfile.TarInfo(name=symlink_name)
            sym.type = tarfile.SYMTYPE
            sym.linkname = "/etc/passwd"
            tf.addfile(sym)
    return buf.getvalue()


class TestStdlibScaffoldingDecoupling:
    """Verify `plugin_registry.scaffolding` imports and runs without Django configured or installed."""

    def test_import_and_manifest_without_django_settings_or_django_module(self):
        script = (
            "import sys; sys.modules['django'] = None; "
            "from plugin_registry.scaffolding import SiteManifest, ProjectGenerator, cli_runner; "
            "m = SiteManifest(project_name='pure_stdlib_site', plugins=['erp']); "
            "m.validate(); "
            "assert 'crm' in m.plugins; "
            "assert ProjectGenerator(m).source_root.is_dir(); "
            "print('STDLIB_OK')"
        )
        env = {k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE"}
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "STDLIB_OK" in result.stdout


class TestCliRunnerParity:
    """Verify pure-stdlib `cli_runner.execute_scaffolding` matches `manage.py create_site` behavior."""

    def test_execute_scaffolding_non_interactive_and_dry_run(self, tmp_path):
        out = io.StringIO()
        manifest_file = tmp_path / "m.json"
        dry_res = execute_scaffolding(
            {
                "project_name": "runner_demo",
                "plugins": "erp",
                "no_input": True,
                "dump_manifest": str(manifest_file),
                "dry_run": True,
            },
            stdout=out,
        )
        assert dry_res is None
        assert manifest_file.is_file()
        loaded = SiteManifest.from_json_file(manifest_file)
        assert loaded.plugins == ["crm", "erp"]

        target = tmp_path / "runner_site"
        dest = execute_scaffolding(
            {
                "project_name": "runner_demo",
                "target_dir": str(target),
                "plugins": "polls",
                "include_docker": False,
                "no_input": True,
            },
            stdout=out,
            source_root=REPO_ROOT,
        )
        assert dest == target.resolve()
        assert (target / "manage.py").is_file()
        assert (target / "polls").is_dir()
        assert "Next Steps:" in out.getvalue()

    def test_execute_scaffolding_interactive_prompts(self, tmp_path):
        target = tmp_path / "prompted_site"
        stdin = io.StringIO(
            f"prompted_site\nPrompted Title\nDesc\n{target}\ntailwind\nen,es\ntodo\nsqlite\nn\n"
        )
        out = io.StringIO()
        dest = execute_scaffolding({}, stdout=out, stdin=stdin, source_root=REPO_ROOT)
        assert dest == target.resolve()
        saved = SiteManifest.from_json_file(target / "site_manifest.json")
        assert saved.theme == "tailwind"
        assert saved.plugins == ["todo"]
        assert saved.include_docker is False


class TestTemplateFetcher:
    """Verify local, HTTPS archive, and git template acquisition with security guards."""

    def test_local_template_dir_and_invalid_dir(self, tmp_path):
        fake_root = _make_fake_template(tmp_path / "repo")
        with resolve_template_source(template_dir=str(fake_root)) as resolved:
            assert resolved == fake_root.resolve()
            assert is_valid_template_root(resolved)

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(TemplateFetchError, match="not a valid"):
            with resolve_template_source(template_dir=str(empty_dir)):
                pass

    def test_zip_archive_download_with_wrapper_dir_and_sha256(self, tmp_path):
        payload = _build_zip_bytes(
            {
                "enterprise_website-main/manage.py": b"#!/usr/bin/env python\n",
                "enterprise_website-main/enterprise_website/__init__.py": b"",
                "enterprise_website-main/plugin_registry/__init__.py": b"",
            }
        )
        digest = hashlib.sha256(payload).hexdigest()
        mock_resp = MagicMock()
        mock_resp.read.side_effect = [payload, b""]
        mock_resp.__enter__.return_value = mock_resp

        with patch("create_enterprise_site.fetcher.urllib.request.urlopen", return_value=mock_resp):
            with resolve_template_source(
                template_url="https://example.com/archive.zip",
                template_sha256=digest,
            ) as resolved:
                assert is_valid_template_root(resolved)
                assert resolved.name == "enterprise_website-main"
            assert not resolved.exists()

    def test_archive_rejects_bad_sha256_and_http_scheme(self):
        with pytest.raises(TemplateFetchError, match="https://"):
            with resolve_template_source(template_url="http://example.com/archive.zip"):
                pass

        mock_resp = MagicMock()
        mock_resp.read.side_effect = [b"corrupt", b""]
        mock_resp.__enter__.return_value = mock_resp
        with patch("create_enterprise_site.fetcher.urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(TemplateFetchError, match="SHA-256 mismatch"):
                with resolve_template_source(
                    template_url="https://example.com/archive.zip",
                    template_sha256="0" * 64,
                ):
                    pass

    def test_zip_slip_and_tar_slip_rejected(self):
        evil_zip = _build_zip_bytes({"../evil.txt": b"pwned"})
        mock_zip = MagicMock()
        mock_zip.read.side_effect = [evil_zip, b""]
        mock_zip.__enter__.return_value = mock_zip
        with patch("create_enterprise_site.fetcher.urllib.request.urlopen", return_value=mock_zip):
            with pytest.raises(TemplateFetchError, match="Zip-Slip"):
                with resolve_template_source(template_url="https://example.com/evil.zip"):
                    pass

        evil_tar = _build_tar_gz_bytes({"repo/manage.py": b"ok"}, symlink_name="repo/bad_link")
        mock_tar = MagicMock()
        mock_tar.read.side_effect = [evil_tar, b""]
        mock_tar.__enter__.return_value = mock_tar
        with patch("create_enterprise_site.fetcher.urllib.request.urlopen", return_value=mock_tar):
            with pytest.raises(TemplateFetchError, match="Unsafe link"):
                with resolve_template_source(template_url="https://example.com/evil.tar.gz"):
                    pass

    def test_mocked_git_clone_success_and_failure(self):
        def fake_clone(cmd, **kwargs):
            clone_dest = Path(cmd[-1])
            _make_fake_template(clone_dest)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with (
            patch("create_enterprise_site.fetcher.shutil.which", return_value="/usr/bin/git"),
            patch("create_enterprise_site.fetcher.subprocess.run", side_effect=fake_clone) as mock_run,
        ):
            with resolve_template_source(git_url="https://example.com/org/repo.git", branch="dev") as resolved:
                assert is_valid_template_root(resolved)
                cmd = mock_run.call_args.args[0]
                assert "--depth" in cmd and "1" in cmd and "dev" in cmd

        with pytest.raises(TemplateFetchError, match="Unsupported git URL"):
            with resolve_template_source(git_url="ext::sh -c id"):
                pass


class TestCreateEnterpriseSiteCli:
    """End-to-end tests for `create_enterprise_site.cli.main` and `python -m create_enterprise_site`."""

    def test_cli_main_generates_minimal_site_and_runs_check_and_migrate(self, tmp_path):
        target = tmp_path / "minimal_cli_site"
        out, err = io.StringIO(), io.StringIO()
        code = cli_main(
            [
                "minimal_cli_site",
                "--no-input",
                "--plugins",
                "none",
                "--no-docker",
                "--target-dir",
                str(target),
                "--template-dir",
                str(REPO_ROOT),
            ],
            stdout=out,
            stderr=err,
        )
        assert code == 0, err.getvalue()
        assert err.getvalue() == ""
        assert (target / "manage.py").is_file()
        assert not (target / "crm").exists()
        assert not (target / "docker-compose.yml").exists()

        check_res = _run_generated_manage(target, "check")
        assert check_res.returncode == 0, check_res.stderr
        migrate_res = _run_generated_manage(target, "migrate", "--noinput")
        assert migrate_res.returncode == 0, migrate_res.stderr

    def test_python_m_create_enterprise_site_generates_full_site_without_django_settings(self, tmp_path):
        target = tmp_path / "full_cli_site"
        env = {k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE"}
        env["PYTHONPATH"] = str(REPO_ROOT)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "create_enterprise_site",
                "full_cli_site",
                "--no-input",
                "--plugins",
                "all",
                "--theme",
                "tailwind",
                "--languages",
                "en,es",
                "--target-dir",
                str(target),
                "--template-dir",
                str(REPO_ROOT),
            ],
            cwd=str(tmp_path),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "Next Steps:" in result.stdout
        assert (target / "manage.py").is_file()
        assert (target / "crm").is_dir()
        assert (target / "erp").is_dir()
        assert (target / "docker-compose.yml").is_file()

        check_res = _run_generated_manage(target, "check")
        assert check_res.returncode == 0, check_res.stderr
        migrate_res = _run_generated_manage(target, "migrate", "--noinput")
        assert migrate_res.returncode == 0, migrate_res.stderr

    def test_cli_dry_run_dump_manifest_and_error_exit_code(self, tmp_path):
        manifest_path = tmp_path / "cli_manifest.json"
        out, err = io.StringIO(), io.StringIO()
        code = cli_main(
            [
                "dry_cli_site",
                "--no-input",
                "--plugins",
                "erp",
                "--dry-run",
                "--dump-manifest",
                str(manifest_path),
            ],
            stdout=out,
            stderr=err,
        )
        assert code == 0, err.getvalue()
        assert manifest_path.is_file()
        assert "Dry run complete" in out.getvalue()

        bad_code = cli_main(
            ["bad_site", "--no-input", "--template-dir", str(tmp_path / "missing_repo")],
            stdout=out,
            stderr=err,
        )
        assert bad_code == 1
        assert "Error:" in err.getvalue()
