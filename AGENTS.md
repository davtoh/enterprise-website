# Project & Modernization AI Guidelines

Welcome to the project repository. When working on modernization, debugging, feature enhancement, or cross-language migrations within this codebase, all AI assistants and developers must adhere to the following rules:

---

## 1. Comment & Reference Preservation
- **Never delete reference comments:** Retain developer notes, stack overflow links, documentation URLs, and tutorial references (e.g., `# https://stackoverflow.com/...`).
- **Preserve user checklists:** Keep user notes and checklist files (such as `NOTES.txt`, `TODO.txt`) intact.
- **Annotate legacy code:** When deprecating or refactoring patterns, annotate rather than erase so learning context remains accessible.

---

## 2. Persistent Task & Migration Logging
- **Always update the migration log:** Maintain `MIGRATION_LOG.md` (and `TODO_MODERNIZATION.md`) with explicit checkpoints.
- **Quota & Token Boundary Resilience:** Log current state, completed items, files touched, and next steps before executing heavy tasks.
- If a session terminates or runs out of quota, any subsequent AI instance can read `MIGRATION_LOG.md` and immediately resume without redundant analysis.

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
- **Bootstrap 4.x & Spacing Compatibility:**
  - Layout is built on Bootstrap 4 (`static/css/bootstrap.css`).
  - Bootstrap 4 does not support flex `gap-*` utilities; always use margin utilities (`mr-*`, `me-*`) or inline margin styling.
- **FontAwesome 4.x Icon Prefix:**
  - Always prefix icons with `fa fa-<name>` (e.g., `fa fa-tasks`). Omitting `fa` causes empty square glyphs.
- **Interactive Component Data Attributes:**
  - Modals and toggles must declare dual data attributes: `data-toggle="modal" data-bs-toggle="modal"` and `data-target="#id" data-bs-target="#id"`.
- **Port Security & Docker Overrides:**
  - Never expose internal database/cache ports in `docker-compose.yml`. Host port bindings belong strictly in `docker-compose.override.yml`.

---

*Detailed modular rules are located in `.agents/rules/`.*
