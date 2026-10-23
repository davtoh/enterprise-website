# Enterprise Website

A modular enterprise web portal built with **Django 5.0**, **Channels / Daphne** (WebSockets/ASGI), **Django REST Framework**, and **Django-Allauth**. Designed to be completely OS-agnostic (runs on Linux, macOS, and Windows) with zero setup required for local development.

This project provides a robust base web platform for industrial or commercial businesses looking to present their products and services, manage user profiles, offer interactive tools (such as task management and voting polls), and engage international clients with multi-language localization.

---

## Complete Documentation Reference

For an in-depth architectural breakdown, directory layout, application modules, system workflows (authentication, voting, and translation sequence diagrams), and complete administrative flows, see the dedicated documentation:

👉 **[Complete Project & Architecture Manual](documentation/README.md)** *(or [`documentation/README.md`](file:///g:/Mi%20unidad/projects/web_and_services/enterprise_website/documentation/README.md))*

---

## Key Features

- **Modern Django Stack:** Powered by Django 5.0 on Python 3.12 with async ASGI support via Channels & Daphne.
- **Cross-Platform & OS-Agnostic:** Runs on Windows, Linux, and macOS without machine-dependent hardcoded configurations.
- **Zero-Barrier Local Development:** Out-of-the-box local SQLite database mode (no MySQL or C++ compiler required).
- **Production-Ready Database Support:** Switch seamlessly to MySQL or PostgreSQL using `.env` environment variables.
- **Authentication & User Management:** Custom `SiteUser` model, Google OAuth2 social login via `django-allauth`, international phone number validation, and country pickers.
- **Internationalization (i18n):** Multi-language catalog support across 5 target locales (`es`, `fr`, `it`, `ja`, `pt`) with web translation via `django-rosetta` and automated baseline generation.
- **Interactive Modules:** Integrated Todo task manager, Polls voting system, and client-side Python execution (Brython).
- **RESTful API:** Ready-to-use Django REST Framework endpoints.

---

## Quickstart Guide

### 1. Prerequisites
- **Python 3.12** (or Python >= 3.10)
- Git

---

### 2. Setup Virtual Environment

#### On Windows (PowerShell):
```powershell
# Clone the repository
git clone https://github.com/davtoh/enterprise-website.git
cd enterprise-website

# Create and activate virtual environment
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install base dependencies
pip install -r requirements.txt
```

#### On Linux / macOS (Bash / Zsh):
```bash
# Clone the repository
git clone https://github.com/davtoh/enterprise-website.git
cd enterprise-website

# Create and activate virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install base dependencies
pip install -r requirements.txt
```

---

### 3. Environment Configuration

Copy the sample environment file:
```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

By default, `.env` is configured with:
```ini
USE_SQLITE=True
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```
This allows the application to run immediately on any operating system without configuring external database servers.

---

### 4. Database Setup & Migrations

Run database migrations:
```powershell
# Windows
.\.venv\Scripts\python.exe manage.py migrate

# Linux / macOS
python manage.py migrate
```

Create an admin superuser:
```powershell
# Windows
.\.venv\Scripts\python.exe manage.py createsuperuser --username=admin --email=admin@example.com

# Linux / macOS
python manage.py createsuperuser --username=admin --email=admin@example.com
```

*(Optional)* Create debug testing users:
```powershell
.\.venv\Scripts\python.exe manage.py populate_users --test
```
> [!WARNING]
> `--test` creates standard generic users (`superuser`, `staff`, `regular`) with passwords equal to their usernames. Use strictly for local debugging and testing, **never** on production servers.

---

### 5. Running the Application

Start the local development server:
```powershell
# Windows
.\.venv\Scripts\python.exe manage.py runserver

# Linux / macOS
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.
- **Main Site:** `http://127.0.0.1:8000/`
- **Admin Panel:** `http://127.0.0.1:8000/admin/`
- **REST API:** `http://127.0.0.1:8000/rest_api/`
- **Rosetta Translations:** `http://127.0.0.1:8000/rosetta/`

---

## Maintenance & Operations Commands

Always execute maintenance commands using the project virtual environment (`.\.venv\Scripts\python.exe` on Windows or with `.venv` active on Linux/macOS).

### Internationalization (i18n) & Translation Pipeline

```powershell
# 1. Extract untranslated strings from templates & code into catalogs (.po)
.\.venv\Scripts\python.exe manage.py makemessages --all --ignore=.venv

# 2. Automatically translate all untranslated strings across configured languages (es, fr, it, ja, pt)
.\.venv\Scripts\python.exe manage.py auto_translate

# 3. Translate a single language (e.g. Spanish)
.\.venv\Scripts\python.exe manage.py auto_translate --lang es

# 4. Use DeepL or OpenAI backends (requires DEEPL_AUTH_KEY or OPENAI_API_KEY in .env)
.\.venv\Scripts\python.exe manage.py auto_translate --backend deepl
.\.venv\Scripts\python.exe manage.py auto_translate --backend openai

# 5. Mark as final immediately without the 'fuzzy' flag
.\.venv\Scripts\python.exe manage.py auto_translate --no-fuzzy

# 6. Compile catalogs (.po -> .mo) for runtime use
.\.venv\Scripts\python.exe manage.py compilemessages --ignore=.venv
```

> [!NOTE]
> If running on Windows and gettext tools are not found (`Can't find msguniq...`), install the GNU gettext tools from [mlocati gettext-iconv-windows](https://mlocati.github.io/articles/gettext-iconv-windows.html) and restart your terminal.

---

### Pre-loaded Databases & Location Fixtures

To populate countries, states, and cities from `world.sql`:
```powershell
.\.venv\Scripts\python.exe manage.py populate_locations
```
*Note: The first execution parses `world.sql` and creates a local cache (`world.sql.json`) for high-speed subsequent runs.*

---

### Automated Test Suite & Coverage

The project uses `pytest` and `pytest-django` for automated unit and integration tests across all apps, with coverage tracked via `pytest-cov`.

#### Running Tests

```powershell
# Windows
.\.venv\Scripts\python.exe -m pytest

# Linux / macOS
python -m pytest
```

#### Running with HTML & Terminal Coverage Report

```powershell
# Windows
.\.venv\Scripts\python.exe -m pytest --cov=. --cov-report=html --cov-report=term

# Linux / macOS
pytest --cov=. --cov-report=html --cov-report=term
```

- **Target Coverage:** $\ge$ 80% (Achieved: 80% with 106 passing tests across all modules)
- **HTML Report Location:** `htmlcov/index.html` (open in browser to inspect statement-by-statement coverage)

---

## Production Deployment (MySQL / PostgreSQL & ASGI)


1. **Setup Production Database (e.g., MySQL on Linux):**
   ```bash
   sudo apt update
   sudo apt install mysql-server libmysqlclient-dev
   sudo mysql_secure_installation
   ```
   Create database and dedicated user:
   ```sql
   CREATE DATABASE productsDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'enterprise_user'@'localhost' IDENTIFIED BY 'YourStrongPasswordHere!';
   GRANT ALL PRIVILEGES ON productsDB.* TO 'enterprise_user'@'localhost' WITH GRANT OPTION;
   FLUSH PRIVILEGES;
   ```

2. **Update `.env`:**
   ```ini
   DEBUG=False
   SECRET_KEY=your-strong-production-secret-key
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   USE_SQLITE=False
   DB_ENGINE=django.db.backends.mysql
   DB_NAME=productsDB
   DB_USER=enterprise_user
   DB_PASSWORD=YourStrongPasswordHere!
   DB_HOST=127.0.0.1
   DB_PORT=3306
   ```

3. **Install Production Requirements & Migrate:**
   ```bash
   pip install -r requirements/production.txt
   python manage.py migrate
   ```

4. **Run with Daphne (ASGI):**
   ```bash
   daphne -b 0.0.0.0 -p 8000 enterprise_website.asgi:application
   ```

---

## Documentation Index

- [Architecture & Operations Manual](documentation/README.md)
- [Modernization Roadmap & Audit](TODO_MODERNIZATION.md)
- [Migration & Checkpoint Log](MIGRATION_LOG.md)
- [AI & Coding Guidelines](AGENTS.md)
