"""Multi-strategy template source acquisition for `create-enterprise-site`."""

from contextlib import contextmanager
import hashlib
import ipaddress
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tarfile
import tempfile
from typing import Iterator, Optional, Union
from urllib.error import URLError
from urllib.parse import urlparse
import urllib.request
import zipfile

DEFAULT_GIT_BRANCH = "main"
_REQUIRED_MARKERS = ("manage.py", "enterprise_website", "plugin_registry")
_DOWNLOAD_CHUNK_SIZE = 65536
_ZIP_SYMLINK_MODE = 0o120000
_UNIX_FILE_TYPE_MASK = 0o170000
_BLOCKED_HOSTNAMES = frozenset({"localhost", "localhost.localdomain", "metadata.google.internal", "metadata"})
_BLOCKED_HOST_SUFFIXES = (".localhost", ".local", ".internal")


class TemplateFetchError(RuntimeError):
    """Raised when a template repository or archive cannot be fetched or validated."""


def is_valid_template_root(path: Path) -> bool:
    """Return True when `path` looks like an enterprise_website template root."""
    if not path.is_dir():
        return False
    return (
        (path / "manage.py").is_file()
        and (path / "enterprise_website").is_dir()
        and (path / "plugin_registry").is_dir()
    )


def _find_template_root(base_dir: Path) -> Path:
    """Locate the template root directly at `base_dir` or inside a single archive wrapper folder."""
    if is_valid_template_root(base_dir):
        return base_dir
    if base_dir.is_dir():
        children = [child for child in base_dir.iterdir() if child.name != "__MACOSX"]
        if len(children) == 1 and children[0].is_dir() and is_valid_template_root(children[0]):
            return children[0]
    markers = ", ".join(_REQUIRED_MARKERS)
    raise TemplateFetchError(
        f"Directory '{base_dir}' is not a valid enterprise_website template root (expected {markers})."
    )


def _is_disallowed_ip(ip: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> bool:
    """Return True for private, loopback, link-local, multicast, reserved, or non-global IPs."""
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None and _is_disallowed_ip(mapped):
        return True
    return (
        not ip.is_global
        or ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _validate_public_host(hostname: Optional[str], port: Optional[int], label: str = "Template archive URL") -> None:
    """Reject local, metadata, and private-network targets to prevent SSRF."""
    host = (hostname or "").strip().rstrip(".").lower()
    if not host or "%" in host:
        raise TemplateFetchError(f"{label} has an invalid host {hostname!r}.")
    if host in _BLOCKED_HOSTNAMES or host.endswith(_BLOCKED_HOST_SUFFIXES):
        raise TemplateFetchError(f"{label} host {hostname!r} is disallowed (private/local/metadata endpoint).")

    try:
        ip_literal = ipaddress.ip_address(host)
    except ValueError:
        ip_literal = None

    if ip_literal is not None:
        if _is_disallowed_ip(ip_literal):
            raise TemplateFetchError(f"{label} target IP {ip_literal} is disallowed (non-public address).")
        return

    try:
        addr_infos = socket.getaddrinfo(host, port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return
    for _, _, _, _, sockaddr in addr_infos:
        resolved_ip = ipaddress.ip_address(sockaddr[0].split("%", 1)[0])
        if _is_disallowed_ip(resolved_ip):
            raise TemplateFetchError(f"{label} host {hostname!r} resolves to disallowed IP {resolved_ip}.")


def _validate_https_url(url: str, label: str = "Template URL") -> None:
    """Enforce HTTPS scheme, non-empty public host, and no embedded credentials."""
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() != "https" or not parsed.netloc or not parsed.hostname:
        raise TemplateFetchError(f"{label} must be a valid https:// URL, got {url!r}.")
    if parsed.username or parsed.password:
        raise TemplateFetchError(f"{label} must not embed credentials, got {url!r}.")
    _validate_public_host(parsed.hostname, parsed.port, label=label)


def _validate_git_url(url: str) -> None:
    """Validate git remote URL, rejecting insecure or arbitrary transport schemes."""
    cleaned = url.strip()
    if not cleaned or cleaned.startswith("ext::"):
        raise TemplateFetchError(f"Unsupported git URL {url!r}.")
    if cleaned.startswith("git@") and ":" in cleaned:
        return
    parsed = urlparse(cleaned)
    if parsed.scheme.lower() not in ("https", "ssh") or not parsed.netloc:
        raise TemplateFetchError(f"Git URL must use https://, ssh://, or git@host:repo, got {url!r}.")


def _download_archive(url: str, dest_file: Path, expected_sha256: Optional[str]) -> None:
    """Download a remote archive over HTTPS and verify optional SHA-256 checksum."""
    _validate_https_url(url, label="Template archive URL")
    hasher = hashlib.sha256()
    try:
        with urllib.request.urlopen(url, timeout=60) as response, dest_file.open("wb") as out:
            final_url = response.geturl()
            if isinstance(final_url, str) and final_url and final_url != url:
                _validate_https_url(final_url, label="Template archive redirect URL")
            while True:
                chunk = response.read(_DOWNLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)
                out.write(chunk)
    except (URLError, OSError) as exc:
        raise TemplateFetchError(f"Failed to download template archive from {url!r}: {exc}") from exc

    if expected_sha256:
        actual = hasher.hexdigest().lower()
        expected = expected_sha256.strip().lower()
        if actual != expected:
            raise TemplateFetchError(
                f"SHA-256 mismatch for {url!r}: expected {expected}, got {actual}."
            )


def _safe_extract_zip(archive_path: Path, extract_dir: Path) -> None:
    """Extract a ZIP archive after rejecting symlinks and path-traversal (Zip-Slip) entries."""
    root = extract_dir.resolve()
    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            for info in zf.infolist():
                if (info.external_attr >> 16) & _UNIX_FILE_TYPE_MASK == _ZIP_SYMLINK_MODE:
                    raise TemplateFetchError(f"Unsafe symlink member in zip archive: {info.filename!r}")
                member_path = Path(info.filename)
                if member_path.is_absolute() or not (root / member_path).resolve().is_relative_to(root):
                    raise TemplateFetchError(f"Unsafe Zip-Slip path detected in archive: {info.filename!r}")
            zf.extractall(root)
    except (zipfile.BadZipFile, OSError) as exc:
        raise TemplateFetchError(f"Invalid ZIP archive '{archive_path}': {exc}") from exc


def _safe_extract_tar(archive_path: Path, extract_dir: Path) -> None:
    """Extract a TAR/TAR.GZ archive after rejecting symlinks and path-traversal entries."""
    root = extract_dir.resolve()
    try:
        with tarfile.open(archive_path, "r:*") as tf:
            members = tf.getmembers()
            for member in members:
                if member.issym() or member.islnk():
                    raise TemplateFetchError(f"Unsafe link member in tar archive: {member.name!r}")
                member_path = Path(member.name)
                if member_path.is_absolute() or not (root / member_path).resolve().is_relative_to(root):
                    raise TemplateFetchError(f"Unsafe Tar-Slip path detected in archive: {member.name!r}")
            tf.extractall(root, members=members)
    except (tarfile.TarError, OSError) as exc:
        raise TemplateFetchError(f"Invalid TAR archive '{archive_path}': {exc}") from exc


def _extract_archive(archive_path: Path, extract_dir: Path, source_url: str) -> Path:
    """Extract `.zip` or `.tar.gz`/`.tgz`/`.tar` archive and return located template root."""
    url_path = urlparse(source_url).path.lower()
    if url_path.endswith(".zip") or zipfile.is_zipfile(archive_path):
        _safe_extract_zip(archive_path, extract_dir)
    elif url_path.endswith((".tar.gz", ".tgz", ".tar")) or tarfile.is_tarfile(archive_path):
        _safe_extract_tar(archive_path, extract_dir)
    else:
        raise TemplateFetchError(
            f"Unsupported archive format for {source_url!r}; expected .zip, .tar.gz, .tgz, or .tar."
        )
    return _find_template_root(extract_dir)


def _clone_git_repo(git_url: str, branch: str, clone_dir: Path) -> Path:
    """Perform a shallow `git clone --depth 1` into `clone_dir` and return template root."""
    _validate_git_url(git_url)
    git_bin = shutil.which("git")
    if not git_bin:
        raise TemplateFetchError("`git` executable not found on PATH; pass --template-dir or --template-url instead.")
    result = subprocess.run(
        [git_bin, "clone", "--depth", "1", "--branch", branch, git_url, str(clone_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise TemplateFetchError(f"git clone failed for {git_url!r} (branch {branch!r}): {detail}")
    return _find_template_root(clone_dir)


@contextmanager
def resolve_template_source(
    template_dir: Optional[str] = None,
    template_url: Optional[str] = None,
    template_sha256: Optional[str] = None,
    git_url: Optional[str] = None,
    branch: Optional[str] = None,
) -> Iterator[Path]:
    """Yield a validated template root directory, cleaning up any temporary downloads/clones."""
    if template_dir:
        yield _find_template_root(Path(template_dir).resolve())
        return

    resolved_url = (template_url or os.getenv("ENTERPRISE_SITE_TEMPLATE_URL", "")).strip()
    if resolved_url:
        with tempfile.TemporaryDirectory(prefix="ces_archive_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            archive_file = tmp_path / "template_archive"
            _download_archive(resolved_url, archive_file, template_sha256)
            extract_dir = tmp_path / "extracted"
            extract_dir.mkdir(parents=True, exist_ok=True)
            yield _extract_archive(archive_file, extract_dir, resolved_url)
            return

    resolved_git = (git_url or os.getenv("ENTERPRISE_SITE_GIT_URL", "")).strip()
    if resolved_git:
        resolved_branch = (branch or os.getenv("ENTERPRISE_SITE_GIT_BRANCH", "") or DEFAULT_GIT_BRANCH).strip()
        with tempfile.TemporaryDirectory(prefix="ces_git_") as tmp_dir:
            clone_dir = Path(tmp_dir) / "repo"
            yield _clone_git_repo(resolved_git, resolved_branch, clone_dir)
            return

    for candidate in (Path.cwd(), Path(__file__).resolve().parents[1]):
        if is_valid_template_root(candidate):
            yield candidate.resolve()
            return

    raise TemplateFetchError(
        "Could not locate an enterprise_website template root. Pass --template-dir, --template-url "
        "(or ENTERPRISE_SITE_TEMPLATE_URL), or --git-url (or ENTERPRISE_SITE_GIT_URL)."
    )
