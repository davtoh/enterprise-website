# Rule: Environment Discovery & Execution Standards

## Purpose
Prevent redundant searching, failed commands, and tool timeouts when running management commands or scripts across sessions. All AI assistants must immediately reference this document before executing project commands.

## Python Virtual Environment
- **Local Virtualenv Path:** `.\.venv\` (relative to project root: `G:\Mi unidad\projects\web_and_services\enterprise_website\.venv\`).
- **Python Executable (Windows / PowerShell):**
  ```powershell
  .\.venv\Scripts\python.exe
  ```
- **Pip Executable:**
  ```powershell
  .\.venv\Scripts\pip.exe
  ```
- **Django Version Installed:** Django 5.x in `.\.venv\`.
- **Note on system `python`:** The global Windows path points to Microsoft Store stub / Python 3.14 which lacks project dependencies. **Do not use plain `python manage.py`**. Always invoke `.\.venv\Scripts\python.exe manage.py`.

## Running Management Commands
- Running migrations:
  ```powershell
  .\.venv\Scripts\python.exe manage.py migrate
  ```
- Running system checks:
  ```powershell
  .\.venv\Scripts\python.exe manage.py check
  ```
- Querying data or executing one-liners (pass command to `shell -c`):
  ```powershell
  .\.venv\Scripts\python.exe manage.py shell -c "from user_management.models import SiteUser; print(SiteUser.objects.count())"
  ```
- Creating users:
  ```powershell
  .\.venv\Scripts\python.exe manage.py createsuperuser
  ```

## Authentication & User Architecture Knowledge
- **Custom User Model:** `AUTH_USER_MODEL = 'user_management.SiteUser'`
- **Portal Separation:**
  - Front-end / Customer Portal: `/accounts/login/` (allows any active `SiteUser`).
  - Administration Backend: `/admin/login/` (requires `is_staff=True` or `is_superuser=True`).
- **Default Users:** The project uses a fresh local SQLite database by default (`USE_SQLITE=True`); initially there are 0 users until created via `createsuperuser` or `/accounts/signup/`.
