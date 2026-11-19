# `create-enterprise-site` & `manage.py create_site` — Composable Scaffolding Wizard

Generate a standalone, production-ready Django + Wagtail project from the `enterprise_website` template—either via the zero-dependency **`create-enterprise-site`** pip CLI or the in-repo **`manage.py create_site`** command—including only the core platform apps and the optional `AppPlugin` modules you select (with automatic transitive dependency resolution).

---

## Pre-Run Verification

Run these checks before scaffolding a new site:

```powershell
# Standalone CLI (when installed via pip)
create-enterprise-site --version

# In-repo Django check & scaffolding test suite
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe -m pytest tests/test_create_enterprise_site_cli.py tests/test_create_site.py tests/test_create_site_command.py
```

---

## CLI Options Reference

| Flag | Default | Description |
| :--- | :--- | :--- |
| `project_name` | `enterprise_site` | Positional Python package name (`^[a-z][a-z0-9_]*$`). |
| `--display-name` | Title-cased `project_name` | Human-readable site title. |
| `--description` | `"Enterprise Django starter platform."` | Short project description. |
| `--target-dir` | `./<project_name>` | Output directory for the generated project. |
| `--theme` | `bootstrap5` | Frontend CSS framework: `bootstrap5`, `tailwind`, or `minimal`. |
| `--languages` | `en,es` | Comma-separated locale codes from `en, es, pt, fr, it, ja` (`en` is always included). |
| `--plugins` | All optional plugins | Comma-separated optional plugins (`todo, polls, webprogram, rest_api, task_runner, video_gallery, crm, erp, intelligent_tracker_hub`), `all`, or `none`. |
| `--database` | `sqlite` | Database backend: `sqlite`, `postgres`, or `mysql`. |
| `--docker` / `--no-docker` | `--docker` | Include or omit `Dockerfile`, `docker-compose.yml`, and `nginx/` assets. |
| `--labs` / `--no-labs` | `False` (auto `True` if `webprogram` selected) | Enable or disable Labs plugin gating. |
| `--from-manifest <path>` | `None` | Load a declarative `SiteManifest` JSON file and skip interactive prompts. |
| `--dump-manifest <path>` | `None` | Write the resolved `SiteManifest` JSON to `<path>`. |
| `--ai [brief]` | `None` | Infer plugins, theme, database, languages, and homepage copy from a brief using Gemini (or deterministic offline keyword fallback). |
| `--no-input` / `--noinput` | `False` | Skip interactive prompts and use flags/manifest/AI defaults. |
| `--overwrite` | `False` | Allow writing into an existing non-empty target directory. |
| `--i18n` | `False` | Run `manage.py compilemessages` in the generated project. |
| `--dry-run` | `False` | Validate and optionally `--dump-manifest` without generating project files. |

### Template Source Options (`create-enterprise-site` CLI)

| Flag | Default | Description |
| :--- | :--- | :--- |
| `--template-dir <path>` | Auto-detected if inside repo | Path to a local `enterprise_website` repository or template directory. |
| `--template-url <url>` | `ENTERPRISE_SITE_TEMPLATE_URL` | HTTPS URL to a `.zip` or `.tar.gz` template archive (Zip-Slip/Tar-Slip protected). |
| `--template-sha256 <hex>` | `None` | Expected SHA-256 hex digest for `--template-url` archive verification. |
| `--git-url <url>` | `ENTERPRISE_SITE_GIT_URL` | Git repository URL (`https://`, `ssh://`, or `git@...`) for shallow template clone. |
| `--branch <name>` | `main` (`ENTERPRISE_SITE_GIT_BRANCH`) | Git branch or tag to clone when using `--git-url`. |
| `--version` | — | Print the `create-enterprise-site` CLI version and exit. |

| Environment Variable | Required | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `ENTERPRISE_SITE_TEMPLATE_URL` | Optional | `""` | Default HTTPS `.zip`/`.tar.gz` archive URL when `--template-url` is omitted. |
| `ENTERPRISE_SITE_GIT_URL` | Optional | `""` | Default Git URL when `--git-url` is omitted. |
| `ENTERPRISE_SITE_GIT_BRANCH` | Optional | `main` | Default branch/tag when `--branch` is omitted. |

---

## Automatic Transitive Plugin Dependencies

Selecting a downstream plugin automatically includes its required upstream plugins:

- `erp` $\rightarrow$ `crm`
- `intelligent_tracker_hub` $\rightarrow$ `crm`, `video_gallery`, `rest_api`
- `webprogram` $\rightarrow$ sets `enable_labs = True`

---

## AI Blueprint Advisor (`--ai`) Environment Variables

When `--ai` is passed, `create_site` checks for a Gemini API key in the environment. If no key is set or the network is unavailable, it falls back deterministically to the built-in keyword heuristic advisor.

| Environment Variable | Required | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) | Optional | `""` | Enables live Gemini JSON blueprint suggestions. |
| `GEMINI_ADVISOR_MODEL` | Optional | `gemini-2.5-flash` | Overrides the Gemini model name. |
| `GEMINI_API_ENDPOINT` | Optional | Google `v1beta` endpoint | Custom `https://` endpoint for Gemini `generateContent`. |

---

## Scenario Combinations Matrix

| Scenario / Objective | Mode / Inputs | Key Parameters | Exact Runnable Command |
| :--- | :--- | :--- | :--- |
| Standalone CLI Quickstart | Pip package | Positional `project_name` | `create-enterprise-site my_project` |
| Standalone CLI (Local Checkout) | Non-interactive | `--template-dir . --no-input` | `create-enterprise-site acme_core --template-dir . --no-input --plugins none --no-docker` |
| Standalone CLI (Verified Archive) | HTTPS tarball + SHA-256 | `--template-url --template-sha256` | `create-enterprise-site acme_ops --template-url https://github.com/davtoh/enterprise-website/archive/refs/heads/main.tar.gz --template-sha256 <sha256> --no-input --plugins erp` |
| Standalone CLI (Git Branch) | Shallow clone | `--git-url --branch` | `create-enterprise-site acme_ops --git-url https://github.com/davtoh/enterprise-website.git --branch main --no-input --plugins erp` |
| Interactive Wizard (In-Repo) | Terminal prompts | None (interactive) | `.\.venv\Scripts\python.exe manage.py create_site` |
| Minimal Core-Only Site | Non-interactive | `--no-input --plugins none --no-docker` | `.\.venv\Scripts\python.exe manage.py create_site acme_core --no-input --plugins none --theme minimal --no-docker --target-dir ../acme_core` |
| CRM + ERP Operations Portal | Non-interactive | `--plugins erp --database postgres` | `.\.venv\Scripts\python.exe manage.py create_site acme_ops --no-input --plugins erp --theme tailwind --database postgres --target-dir ../acme_ops` |
| AI Blueprint Advisor | Brief + `--ai` | `--ai "..." --no-input` | `.\.venv\Scripts\python.exe manage.py create_site acme_sec --no-input --ai "Security camera surveillance portal with CRM and Spanish support" --target-dir ../acme_sec` |
| Export Declarative Manifest | Dry-run dump | `--dump-manifest --dry-run` | `.\.venv\Scripts\python.exe manage.py create_site acme_ops --no-input --plugins erp,polls --dump-manifest site_manifest.json --dry-run` |
| Reproduce from Manifest | JSON file | `--from-manifest` | `.\.venv\Scripts\python.exe manage.py create_site --from-manifest site_manifest.json --target-dir ../acme_ops_copy` |
