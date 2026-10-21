# Modernization & Production Readiness Audit (TODO & Roadmap)

**Project:** Enterprise Website (Django)  
**Status:** In Progress — Phase 1, 2, 3 & Migration Execution Complete (Django 5.0 on Python 3.12)  
**Primary Goal:** Modernize codebase, ensure cross-platform operability (Linux, macOS, Windows), and establish clean production deployment standards.

---

## 1. Executive Summary & Progress

| Area | Initial Legacy State | Modernized State | Status |
| :--- | :--- | :--- | :--- |
| **Python Version** | Python 3.6/3.7 (EOL) | **Python 3.12.10** | **DONE** |
| **Django Version** | Django 2.0.6 (EOL since 2019) | **Django 5.0.14** | **DONE** |
| **Secrets Handling** | Raw `keys.json` committed with plaintext secrets & passwords | `.env` with `python-dotenv`, secrets excluded in `.gitignore`, `.env.example` template provided | **DONE** |
| **Database Support** | Hardcoded to MySQL via `mysqlclient` (fails if MySQL is not installed locally) | OS-agnostic dynamic `DATABASES`: Default SQLite for 0-setup local run, MySQL/Postgres via `.env` | **DONE** |
| **Timezone Management** | Legacy `django-easy-timezones` with discontinued MaxMind `.dat` | Python 3.12 standard library `zoneinfo` + `tzdata`, graceful signal fallback | **DONE** |
| **Dependencies & Packaging** | Single 44-line `requirements.txt` with legacy comments and unpinned mix | Modular: `requirements/base.txt`, `requirements/local.txt`, `requirements/production.txt` | **DONE** |
| **Django Compatibility Fixes** | `force_text`, invalid escape syntax, `allauth` AccountMiddleware | `force_str`, raw strings in `todo/urls.py` and `utils.py`, `allauth.account.middleware.AccountMiddleware` added | **DONE** |
| **Migrations** | Unapplied migrations | All migrations successfully executed on local database (`python manage.py migrate` OK) | **DONE** |
| **Documentation** | Outdated `README.rst` with syntax errors & Ubuntu-only instructions | Modern `README.md` with cross-platform instructions (Windows PowerShell, Linux/macOS bash) | **DONE** |

---

## 2. Multi-Platform (OS-Agnostic) Strategy

Identical behavior across **Linux**, **macOS**, and **Windows**:
1. **Zero OS-Branching in Settings:**
   - Removed `DB_USER_WINDOWS`, `DB_USER_LINUX`, `DB_USER_DARWIN`.
   - Replaced with standard 12-Factor app environment variables (`.env`).
2. **Unified Path Management:**
   - All directory anchors use `pathlib.Path` (`BASE_DIR / 'staticfiles'`).
3. **Database Flexibility:**
   - `USE_SQLITE=True` enables instant local development out-of-the-box on any OS without requiring C/C++ compilation tools for `mysqlclient`.
   - Production can switch to `DB_ENGINE=django.db.backends.mysql` or `postgresql` simply via `.env`.

---

## 3. Action Plan & Status Checklist

### Phase 1: Security & Hygiene
- [x] Add `keys.json` and `.env` to `.gitignore`.
- [x] Create `.env.example` with template keys and sensible defaults.
- [x] Isolate and ignore local `.sqlite3` and media files.
- [ ] Review removal/archival of 175MB `world.sql` and `world.sql.json` from git history.

### Phase 2: Python & Virtual Environment Setup
- [x] Install Python 3.12 runtime.
- [x] Create isolated `.venv` using Python 3.12.
- [x] Audit requirements and separate into `requirements/base.txt`, `requirements/local.txt`, `requirements/production.txt`.
- [x] Freeze working, tested dependencies into `requirements/base.txt`.

### Phase 3: Django Settings & OS-Agnostic Refactoring
- [x] Replace `custom_tags.management.commands.secret_keys` JSON reading with `python-dotenv`.
- [x] Make `DATABASES` dynamic (SQLite out-of-the-box, configurable MySQL/Postgres in prod).
- [x] Modernize timezone handling using Python 3.12 standard library `zoneinfo`.
- [x] Fix deprecated Django 2.x APIs (`force_text` -> `force_str`, `USE_L10N`, `DEFAULT_AUTO_FIELD`, `allauth.account.middleware.AccountMiddleware`).
- [x] Resolve `SyntaxWarning` invalid escape sequences in `todo/urls.py` and `utils.py`.

### Phase 4: Verification & Migrations
- [x] `python manage.py check` passes with 0 issues.
- [x] `python manage.py showmigrations` and `python manage.py migrate` executed cleanly.
- [ ] Run automated tests (`pytest` / `python manage.py test`).

### Phase 5: Production Readiness & Containerization
- [x] Add cross-platform `README.md` (Windows, Linux, macOS).
- [ ] Add `Dockerfile` and `docker-compose.yml` for containerized multi-platform local run & production deployment.
- [ ] Configure production security headers (`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`).

### Phase 6: Routing, AI Standards & Logic Modernization
- [x] AI Governance: Root `AGENTS.md`, modular `.agents/rules/`, and portable `documentation/GLOBAL_AI_RULES.md` for comment retention, persistent logging, and milestone reviews.
- [x] Persistent Logging: Initialized and actively maintained `MIGRATION_LOG.md`.
- [x] Navigation & Routes: Fixed navbar broken links (`about.html`, `services.html`, etc.) to dynamic Django routes (`home:index`, `home:about`, `home:services`, `home:products`, `home:contact`).
- [x] Content Pages: Built responsive CBVs and templates for About Us, Services, Products, and Contact with backwards-compatible `.html` URL aliases.
- [x] Interactive Modules Menu: Added "Apps" dropdown to navbar linking directly to Todo, Polls, Brython, REST API, and Admin.
- [x] User Management & Auth: Fixed Django 5 LogoutView GET/POST support, base64 encoding/decoding, reverse URLs, and created missing templates (`profile.html`, `logout.html`, `siteuser_list.html`).
- [x] Todo & Polls Logic: Replaced hard lookups with `get_object_or_404()`, fixed typographical curly quotes in templates, and enhanced card styling while preserving all original learning references.
