# Project & Modernization AI Guidelines

Welcome to the project repository. When working on modernization, debugging, feature enhancement, or cross-language migrations within this codebase, all AI assistants and developers must adhere to the following rules:

---

## 1. Comment & Reference Preservation
- **Never delete reference comments:** Retain developer notes, stack overflow links, documentation URLs, and tutorial references (e.g., `# https://stackoverflow.com/...`).
- **Preserve user checklists:** Keep user notes and checklist files (such as `NOTES.txt`, `TODO.txt`) intact.
- **Annotate legacy code:** When deprecating or refactoring patterns, annotate rather than erase so learning context remains accessible.

---

## 2. Persistent Task & Migration Logging
- **Changelog & Plan State Engine:** Record completed milestones and notable fixes via `diagnose.py changelog add` into `CHANGELOG.md` (and track multi-step roadmaps in `.TODO/` / `.frontier/`). Never create or append to `MIGRATION_LOG.md`.
- **Quota & Token Boundary Resilience:** Keep `.frontier/plans/<slug>/` and `.frontier/LEARN_QUEUE.md` up-to-date so any subsequent AI instance can resume immediately via `plan_engine.py status` and `plan_engine.py next`.

---

## 3. Milestone-by-Milestone Workflow & Review
- **Incremental Milestones:** Group work into discrete, self-contained milestones.
- **Automated Verification:** Run automated system checks, route tests, or test suites at the end of each milestone.
- **Manual Verification Guide:** Provide clear, concrete manual testing instructions for the user to verify in their browser or terminal.
- **Pause for User Approval:** Allow the user to review, manually test, and commit their code milestone by milestone.

---

## 4. Security & Engineering Standards
- **OWASP & Framework Security:**
  - Zero plaintext secrets in code; isolate environment variables in `.env` (with `.env.example`).
  - Zero hardcoded infrastructure endpoints: Never embed connection strings (`redis://...`), hostnames/IPs (`127.0.0.1`, `localhost`), credentials, or ports (`6379`, `5432`, `3306`) as fallback defaults in Python code. All endpoints must resolve strictly from environment variables.
  - Strict CSRF protection on POST/PUT requests.
  - Safe error handling: use `get_object_or_404` instead of crashing on `DoesNotExist`.
  - Proper user authentication, permission checks, and safe URL redirects.
- **Cross-Platform Compatibility:**
  - Seamless execution across Windows, Linux, and macOS.
  - OS-agnostic pathing with `pathlib.Path`.
- **Clean Code & Idiomatic Style:**
  - Adhere to PEP 8 standards in Python and official conventions in target migration languages.
  - Maintain clean URL routing using framework reverse helpers (`reverse`, `reverse_lazy`, `{% url %}`).

---

## 5. Environment Discovery & Command Execution
- **Explicit Python Virtual Environment:** Always use the active local virtual environment at `.\.venv\Scripts\python.exe`.
- **Avoid Global `python` Calls:** Global PATH commands (like `python` or `py`) resolve to unconfigured or stub versions without Django dependencies installed.
- **Project Command Invocation:**
  ```powershell
  .\.venv\Scripts\python.exe manage.py <command>
  ```
- **Authentication Model Context:**
  - `AUTH_USER_MODEL = 'user_management.SiteUser'`
  - Front-end auth is at `/accounts/login/` (any active `SiteUser`).
  - Admin auth is at `/admin/login/` (requires `is_staff=True`).

---

## 6. Internationalization (i18n) & Rosetta Translation
- **Mandatory Translation in Templates:** All user-facing strings must load `{% load i18n %}` and use `{% trans "..." %}` or `{% blocktrans %}...{% endblocktrans %}`.
- **Mandatory Translation in Python:**
  - Models, forms, and field labels use `gettext_lazy as _`.
  - Views and flash messages use `gettext as _` (`messages.success(request, _("..."))`).
- **Rosetta Catalog Maintenance:**
  - Keep all catalogs up-to-date with `.\.venv\Scripts\python.exe manage.py makemessages --all --ignore=.venv`.
  - Maintain PO files and compile with `.\.venv\Scripts\python.exe manage.py compilemessages`.
  - Enable machine translation bootstrapping and in-app Rosetta translation suggestions for fast localization.

## 7. Frontend, UI Standards & Port Isolation
- **Bootstrap Modernization & Custom Style Elimination:**
  - Modernized templates (Milestone 12+) standardize on **Bootstrap 5.3+**.
  - **Eliminate custom styles:** Avoid and remove ad-hoc inline styles (`style="..."`) and custom modal hacks. Use framework utilities (`gap-*`, `me-*`, `ms-*`, `d-flex`) and clean semantic classes.
  - Interactive components must migrate from dual `data-toggle`/`data-bs-toggle` to standard native `data-bs-*` attributes (`data-bs-toggle="modal"`, `data-bs-target`, etc.).
- **FontAwesome 4.x Icon Prefix:**
  - Always prefix icons with `fa fa-<name>` (e.g., `fa fa-tasks`). Omitting `fa` causes empty square glyphs.
- **Port Security & Docker Overrides:**
  - Never expose internal database/cache ports in `docker-compose.yml`. Host port bindings belong strictly in `docker-compose.override.yml`.

---

## 8. Plugin Registry, Labs & Unfold Admin Invariants
- **Lazy Model Imports in Plugin Discovery:** `PluginRegistry` and plugin `ready()` hooks execute before Django's app registry is fully populated. Always defer ORM model imports (`PluginState`, `SiteConfiguration`, etc.) inside hook methods/functions (`get_active_plugins()`, etc.) rather than importing models at module top level.
- **PluginRegistry Method Budget & Block ORM Deferral:** Keep `PluginRegistry` within the 12-method class budget by extracting stateless helpers (e.g., `_get_plugin_states`) to module level, and defer ORM imports inside Wagtail block `get_context()` when blocks are referenced by `AppPlugin.stream_blocks`.
- **Labs Plugins URL Prefix:** Every plugin registered with `zone="labs"` must declare an explicit `url_prefix` so dynamic plugin routing stays isolated and never collides with root or CMS routes.
- **Custom Unfold `/admin/*` Route Ordering & Context:** Mount custom `/admin/*` views **before** `path("admin/", admin.site.urls)` in `urlpatterns`, wrap them with `admin.site.admin_view(...)`, and merge `admin.site.each_context(request)` into template context so Unfold navigation, breadcrumbs, and permissions render properly.

---

## 9. Wagtail CMS, Signals & Cache Invariants
- **Wagtail Test Page Attachment & M2M Order:** Attach Wagtail test pages to `Site.objects.get(is_default_site=True).root_page`, and save `BlogPage` instances via `add_child()` before adding `ParentalManyToManyField` categories.
- **Compact CMS Signal Registration & Versioned Cache Keys:** Loop signal connections over model tuples in `register_cms_signals()` to stay under the 40-line function budget, and use versioned cache keys (`cache.incr`) for backend-agnostic menu invalidation.
- **Cache Isolation for `seed_initial_cms_pages()` Tests:** Tests that trigger Wagtail `page_published` signals or `sync_wagtail_menus()` populate `LocMemCache` via `cms/signals.py`. Pytest classes using `seed_initial_cms_pages()` must clear `django.core.cache.cache` in an `autouse` fixture to prevent leaking `main_navigation` into subsequent fallback-nav tests.

---

## 10. Cross-App Models, Forms & Middleware Invariants
- **ModelForm Backfilled Fields:** When backfilling `ModelForm` fields in `model.save()` (e.g., `Invoice.customer_name` from `crm_company`/`crm_contact`), set `blank=True` on the model fields and enforce conditional presence in `Form.clean()`.
- **TimeZone Display & Middleware Activation:** Ensure `TimeZone.__str__` returns a readable label, `TimezoneMiddleware` reads `user.timezone.timezone`, and `TimezoneMiddleware` is registered in `settings.base.MIDDLEWARE` for live activation.

---

*Detailed modular rules are located in `.agents/rules/`.*
