# `manage.py create_site` — Composable Scaffolding Wizard

The `create_site` management command generates a standalone, production-ready Django + Wagtail project from the `enterprise_website` template, including only the core platform apps and the optional `AppPlugin` modules you select (with automatic transitive dependency resolution).

---

## Pre-Run Verification

Run these checks in the repository root before scaffolding a new site:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe -m pytest tests/test_create_site.py
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
| Interactive Wizard | Terminal prompts | None (interactive) | `.\.venv\Scripts\python.exe manage.py create_site` |
| Minimal Core-Only Site | Non-interactive | `--no-input --plugins none --no-docker` | `.\.venv\Scripts\python.exe manage.py create_site acme_core --no-input --plugins none --theme minimal --no-docker --target-dir ../acme_core` |
| CRM + ERP Operations Portal | Non-interactive | `--plugins erp --database postgres` | `.\.venv\Scripts\python.exe manage.py create_site acme_ops --no-input --plugins erp --theme tailwind --database postgres --target-dir ../acme_ops` |
| AI Blueprint Advisor | Brief + `--ai` | `--ai "..." --no-input` | `.\.venv\Scripts\python.exe manage.py create_site acme_sec --no-input --ai "Security camera surveillance portal with CRM and Spanish support" --target-dir ../acme_sec` |
| Export Declarative Manifest | Dry-run dump | `--dump-manifest --dry-run` | `.\.venv\Scripts\python.exe manage.py create_site acme_ops --no-input --plugins erp,polls --dump-manifest site_manifest.json --dry-run` |
| Reproduce from Manifest | JSON file | `--from-manifest` | `.\.venv\Scripts\python.exe manage.py create_site --from-manifest site_manifest.json --target-dir ../acme_ops_copy` |
