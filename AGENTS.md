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

*Detailed modular rules are located in `.agents/rules/`.*
