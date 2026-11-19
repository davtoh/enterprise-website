# Milestone 18 Implementation Plan: Packaging `create-enterprise-site` pip CLI

**Plan Slug:** `create_enterprise_site_pip_cli`  
**Milestone Reference:** `milestone_plan.md` (Milestone 18)  
**Architecture Reference:** `docs/ARCHITECTURE.md` & `documentation/create_site.md`  
**Selected Tier:** Tier 2 — Frontier SOTA (Zero-Django-Dependency Stdlib Scaffolding Engine + Dual Local/Remote Template Acquisition + PEP 621 `pyproject.toml` Console Entry Point)  
**Execution Mode:** 1-Milestone-Per-Turn Execution Gate (`plan_engine.py`)

---

## 1. Executive Summary & 3-Tier Architectural Options

This plan delivers **Milestone 18 (`Packaging: create-enterprise-site pip CLI`)**, enabling developers to scaffold a standalone, customized enterprise Django project via `pip install create-enterprise-site` and `create-enterprise-site my_project` without manually cloning the repository first.

### 3-Tier Architectural Options Evaluated

| Tier | Architecture Pattern | How It Works | Trade-Offs & Verdict |
| :--- | :--- | :--- | :--- |
| **Tier 1: Pragmatic Baseline** | Thin `git clone` + `subprocess` `manage.py create_site` wrapper | Shells out to `git clone` into a temp folder and executes `python manage.py create_site` inside the cloned directory. | **Fragile in clean virtualenvs:** Running `manage.py create_site` boots Django's full `INSTALLED_APPS`, failing with `ModuleNotFoundError` unless all 60+ heavy runtime dependencies (Wagtail, Celery, Unfold, DRF) are pre-installed in the caller's CLI environment. Also fails if `git` is absent. |
| **Tier 2: Frontier SOTA (Recommended Default)** | Zero-Dependency Stdlib Scaffolding Engine + Multi-Strategy Template Fetcher + PEP 621 `pyproject.toml` | Makes `plugin_registry/scaffolding/` runnable on **100% pure Python stdlib** (lazy optional Django lookups in `manifest.py` and `generator.py`), extracts a shared `cli_runner.py` used by both `manage.py create_site` and `create-enterprise-site`, and adds `create_enterprise_site/fetcher.py` supporting local repo/directory (`--template-dir`), HTTPS tarball/zip archive download (`--template-url` with SHA-256 & Zip-Slip guard), and shallow `git clone --depth 1` (`--git-url`). | **Best balance of speed, reliability & zero dependency bloat:** Installs instantaneously in any clean Python environment (`pipx` / `pip`), works offline from local checkouts or archives without requiring `git` or Django pre-installed, and keeps a single source of truth (SSOT) with `manage.py create_site`. |
| **Tier 3: Novel Moonshot** | Self-Contained Embedded Template Wheel + Auto-Virtualenv Bootstrapper | Bundles the entire repository source tree inside wheel package data and automatically creates a target `.venv`, runs `pip install -r requirements.txt`, and executes `migrate` during CLI invocation. | **High wheel bloat & brittle network coupling:** Embeds multi-megabyte static/locale assets into wheel builds and couples CLI runs to live PyPI network installs inside child virtualenvs. |

---

## 2. Quantitative Modularity & Target Budgets

All modified and newly created source files across all 3 milestones must strictly satisfy the project's Modularity Budgets ($\le 350$ lines soft warning, $\le 500$ lines hard ceiling, $\le 12$ methods/class, $\le 40$ lines/function):

| Target File | Current Lines | Planned Net Lines | Budget Status | Responsibility |
| :--- | ---: | ---: | :--- | :--- |
| `plugin_registry/scaffolding/manifest.py` | 264L | ~272L ($\le 12$M, $\le 40$L/fn) | **PASS** (< 350L) | Lazy optional `django.apps` / `plugin_registry` import in `_lookup_plugin_dependencies` |
| `plugin_registry/scaffolding/generator.py` | 127L | ~140L ($\le 12$M, $\le 40$L/fn) | **PASS** (< 350L) | Lazy optional `django.conf.settings` resolution in `ProjectGenerator.__init__` |
| `plugin_registry/scaffolding/__init__.py` | 31L | ~36L | **PASS** (< 350L) | Export pure-stdlib scaffolding primitives and CLI runner helpers |
| `plugin_registry/scaffolding/cli_runner.py` | 0L (New) | ~235L ($\le 40$L/fn) | **PASS** (< 350L) | Shared CLI argument builder, interactive prompts, manifest assembly, next-steps printer |
| `plugin_registry/management/commands/create_site.py` | 242L | ~95L ($\le 40$L/fn) | **PASS** (< 350L) | Thin Django `BaseCommand` adapter delegating to `cli_runner.py` |
| `create_enterprise_site/__init__.py` | 0L (New) | ~20L | **PASS** (< 350L) | Package version and public CLI entry exports |
| `create_enterprise_site/fetcher.py` | 0L (New) | ~185L ($\le 40$L/fn) | **PASS** (< 350L) | Template acquisition (`--template-dir`, HTTPS `.tar.gz`/`.zip` with Zip-Slip & SHA-256 guard, `git clone`) |
| `create_enterprise_site/cli.py` | 0L (New) | ~145L ($\le 40$L/fn) | **PASS** (< 350L) | Standalone `create-enterprise-site` `argparse` entry point (`main(argv)`) |
| `create_enterprise_site/__main__.py` | 0L (New) | ~12L | **PASS** (< 350L) | Support `python -m create_enterprise_site` execution |
| `pyproject.toml` | 0L (New) | ~85L | **PASS** (< 350L) | PEP 621 package metadata, `[project.scripts]` entry point, build-system & pytest config |
| `tests/test_create_enterprise_site_cli.py` | 0L (New) | ~260L ($\le 40$L/fn) | **PASS** (< 350L) | Unit & E2E tests for stdlib decoupling, `fetcher.py`, `create-enterprise-site` CLI, and packaging |

---

## 3. Surface Invariants & Public API Contracts

1. **Backwards-Compatible `manage.py create_site` Contract**:
   - All 17 existing arguments (`project_name`, `--display-name`, `--description`, `--target-dir`, `--theme`, `--languages`, `--plugins`, `--database`, `--docker`/`--no-docker`, `--labs`/`--no-labs`, `--from-manifest`, `--dump-manifest`, `--ai`, `--no-input`/`--noinput`, `--overwrite`, `--i18n`, `--dry-run`) and `CommandError` exception semantics must remain 100% backwards-compatible across `tests/test_create_site.py` and `tests/test_create_site_command.py`.
2. **Pure-Stdlib Execution Without `DJANGO_SETTINGS_MODULE`**:
   - Importing and running `plugin_registry.scaffolding` (`SiteManifest`, `suggest_manifest_from_prompt`, `ProjectGenerator`, `cli_runner`) and `create_enterprise_site.cli:main` in a subprocess without `DJANGO_SETTINGS_MODULE` set must succeed with zero `ImproperlyConfigured` or `AppRegistryNotReady` errors.
3. **Zero Hardcoded Infrastructure & Safe Archive Extraction (OWASP)**:
   - `create_enterprise_site/fetcher.py` must resolve remote template archive/repo URLs from explicit CLI flags (`--template-url`, `--git-url`) or environment variables (`ENTERPRISE_SITE_TEMPLATE_URL`, `ENTERPRISE_SITE_GIT_URL`) with safe HTTPS validation (`https://` scheme enforcement on remote URLs), optional `--template-sha256` integrity verification, and strict path-traversal (Zip-Slip / Tar-Slip) validation before extracting any archive member.
4. **Cross-Platform Binary Write & Temp Cleanup Invariant**:
   - All generated files must use UTF-8 binary writes (`write_bytes`), and temporary directories allocated during archive/git template acquisition must be deterministically cleaned up via context managers (`tempfile.TemporaryDirectory()`).

---

## 4. Scenario Combinations Matrix

| Scenario ID | Milestone | Subsystem Under Test | Verification Command | Expected Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **SC-1801** | Milestone 1 | Pure-stdlib scaffolding import & execution without `DJANGO_SETTINGS_MODULE`, plus `manage.py create_site` regression parity | `pytest tests/test_create_enterprise_site_cli.py tests/test_create_site.py tests/test_create_site_command.py` | 100% pass; `plugin_registry.scaffolding` works without Django configured; all 28 existing `create_site` tests pass |
| **SC-1802** | Milestone 1 | `create_enterprise_site/fetcher.py` template acquisition (local checkout, `.tar.gz`/`.zip` archive with SHA-256 & Zip-Slip rejection, mocked `git clone`) | `pytest tests/test_create_enterprise_site_cli.py -k fetcher` | 100% pass; valid archives extract template root cleanly; traversal members (`../evil`) and bad SHA-256 raise `TemplateFetchError` |
| **SC-1803** | Milestone 2 | `create-enterprise-site` standalone CLI (`main`, `python -m create_enterprise_site`, interactive, `--no-input`, `--from-manifest`, `--dump-manifest`, `--ai`) | `pytest tests/test_create_enterprise_site_cli.py -k cli` | 100% pass; generated standalone project in `tmp_path` passes `manage.py check` and `manage.py migrate --noinput` |
| **SC-1804** | Milestone 3 | Editable package install (`pip install -e . --no-build-isolation --no-deps`), console script entry point, and Code-Doc Sync | `pytest tests/test_create_enterprise_site_cli.py tests/test_create_site.py tests/test_create_site_command.py` | 100% pass; `pyproject.toml` entry point `create-enterprise-site --help` and `--version` succeed; docs & CI match live CLI |

---

## 5. Multi-Phase Roadmap & Milestones

### Milestone 1: Zero-Django-Import Scaffolding Engine Decoupling, Shared CLI Runner & Template Fetcher
- [x] **plugin_registry/scaffolding/manifest.py, plugin_registry/scaffolding/generator.py & plugin_registry/scaffolding/__init__.py**: Decouple top-level Django imports via lazy runtime checks so `SiteManifest`, `ProjectGenerator`, and `plugin_registry.scaffolding` execute in pure Python stdlib without `DJANGO_SETTINGS_MODULE`.
- [x] **plugin_registry/scaffolding/cli_runner.py & plugin_registry/management/commands/create_site.py**: Extract shared CLI argument definitions, interactive prompts, manifest resolution, and next-steps formatting into `plugin_registry/scaffolding/cli_runner.py` and refactor `create_site.py` to delegate to `cli_runner.py`.
- [x] **create_enterprise_site/__init__.py & create_enterprise_site/fetcher.py**: Implement multi-strategy template acquisition (`resolve_template_source`) supporting local directory discovery (`--template-dir`), HTTPS `.zip`/`.tar.gz` archive download with SHA-256 verification and Zip-Slip path-traversal protection (`--template-url`), and shallow `git clone --depth 1` (`--git-url` / `--branch`).
- [x] **tests/test_create_enterprise_site_cli.py**: Add unit tests for pure-stdlib subprocess import/execution without Django settings, `cli_runner` parity, and `fetcher.py` local, archive (including Zip-Slip & checksum failure), and mocked git acquisition.
- [x] **CHANGELOG.md**: Record Milestone 1 completion via `python "<config_dir>/skills/system-diagnostics/scripts/diagnose.py" changelog add`.

### Milestone 2: `create-enterprise-site` Standalone Console Entry Point & PEP 621 `pyproject.toml` Packaging (**DEFERRED TO NEXT TURN / MILESTONE**)
- [ ] **create_enterprise_site/cli.py & create_enterprise_site/__main__.py**: Implement the standalone `create-enterprise-site` CLI entry point (`main(argv)`) integrating `cli_runner` options with template acquisition flags (`--template-dir`, `--template-url`, `--template-sha256`, `--git-url`, `--branch`, `--version`) and deterministic error handling.
- [ ] **pyproject.toml & MANIFEST.in**: Create PEP 621 `pyproject.toml` and `MANIFEST.in` registering `create-enterprise-site = "create_enterprise_site.cli:main"`, package discovery for `create_enterprise_site` and `plugin_registry.scaffolding`, and repository tool metadata.
- [ ] **tests/test_create_enterprise_site_cli.py**: Add end-to-end CLI tests (`create_enterprise_site.cli.main` and `python -m create_enterprise_site`) generating minimal and full projects in `tmp_path` and verifying `manage.py check` and `manage.py migrate --noinput`.
- [ ] **CHANGELOG.md**: Record Milestone 2 completion via `python "<config_dir>/skills/system-diagnostics/scripts/diagnose.py" changelog add`.

### Milestone 3: CI Package Build Pipeline, Root `README.md` Quickstart, Executable Documentation & Milestone 18 Sign-Off (**DEFERRED TO NEXT TURN / MILESTONE**)
- [ ] **.github/workflows/ci.yml**: Add `pip install --no-build-isolation --no-deps -e .` and `create-enterprise-site` smoke verification to the GitHub Actions CI workflow.
- [ ] **README.md, documentation/create_site.md & milestone_plan.md**: Document `pip install create-enterprise-site` and `create-enterprise-site` CLI recipes in `README.md` and `documentation/create_site.md` (with updated Scenario Combinations Matrix), and mark Milestone 18 complete in `milestone_plan.md`.
- [ ] **tests/test_create_enterprise_site_cli.py**: Add `pyproject.toml` console script registration, `--version`, and documentation flag parity tests.
- [ ] **CHANGELOG.md**: Record Milestone 3 completion via `python "<config_dir>/skills/system-diagnostics/scripts/diagnose.py" changelog add`.
