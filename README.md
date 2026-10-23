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

To fetch and populate countries, states, and cities without storing large 175MB SQL files in Git:

1. **Download geodata on-demand:**
   ```powershell
   # Downloads world.sql from upstream repository or archive
   .\.venv\Scripts\python.exe manage.py download_geodata
   ```

2. **Populate database:**
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

- **Target Coverage:** $\ge$ 80% (Achieved: 80% with 109 passing tests across all modules)
- **HTML Report Location:** `htmlcov/index.html` (open in browser to inspect statement-by-statement coverage)

---

## Docker & Containerized Architecture

Enterprise Website includes a multi-stage `Dockerfile`, production `docker-compose.yml`, local live-reload `docker-compose.override.yml`, and `nginx/default.conf` reverse proxy.

### Container Services Stack

| Service | Technology | Role |
| :--- | :--- | :--- |
| `web` | Python 3.12 + Daphne ASGI | Runs Django application, manages WebSocket & HTTP requests as non-root user `appuser` |
| `db` | PostgreSQL 16 Alpine | Relational production database with automated healthcheck |
| `redis` | Redis 7 Alpine | Channel layer backend for WebSockets & future Celery task runner |
| `nginx` | Nginx 1.27 Alpine | High-performance reverse proxy, SSL termination, and static/media file server |

### 1. Local Containerized Development (Live Reload & SQLite)

Run Docker Compose directly with the default `docker-compose.override.yml`:

```bash
docker compose up
```

- Source code is mounted into the container for instant hot-reload.
- Web app accessible at `http://localhost:8000/`.

### 2. Full Production Stack Deployment (PostgreSQL + Redis + Nginx)

Run the production configuration without development overrides:

```bash
# Build and start all services in detached mode
docker compose -f docker-compose.yml up -d --build

# Inspect running container health
docker compose -f docker-compose.yml ps

# Execute management commands inside the container
docker compose -f docker-compose.yml exec web python manage.py check
docker compose -f docker-compose.yml exec web python manage.py migrate
docker compose -f docker-compose.yml exec web python manage.py sync_menus
```

The web application is exposed through Nginx on port `80` (or the port specified in `PORT` in `.env`).

---

## Production Security & Deployment Hardening

Production security settings in `enterprise_website/settings.py` are automatically enabled when `DEBUG=False`:

- **HTTPS Redirection & HSTS:** `SECURE_SSL_REDIRECT = True`, `SECURE_HSTS_SECONDS = 31536000` (1 year), `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`, `SECURE_HSTS_PRELOAD = True`.
- **Cookie Protection:** `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`.
- **Content & Framing Headers:** `X_FRAME_OPTIONS = 'DENY'`, `SECURE_CONTENT_TYPE_NOSNIFF = True`.
- **Reverse Proxy SSL Termination:** `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`.

### Verifying Security Readiness

Run Django's built-in deployment security auditor:
```powershell
# Windows
$env:DEBUG="False"; $env:SECRET_KEY="your-strong-production-key-at-least-50-chars-long"; .\.venv\Scripts\python.exe manage.py check --deploy

# Linux / macOS
DEBUG=False SECRET_KEY="your-strong-production-key-at-least-50-chars-long" python manage.py check --deploy
```

---

## CI/CD Pipeline (GitHub Actions)

Continuous Integration and Delivery is automated via `.github/workflows/ci.yml`:

- **On Pull Request & Push to `master`/`main`:**
  1. Installs Python 3.12 dependencies (`requirements/local.txt` & `requirements/production.txt`).
  2. Compiles translations via `compilemessages`.
  3. Executes `manage.py check` and production `manage.py check --deploy`.
  4. Runs complete test suite with coverage (`pytest --cov=. --cov-report=xml --cov-report=html`).
  5. Uploads HTML coverage report artifact.
- **On Release Tag (`v*`):**
  1. Builds multi-stage production Docker image.
  2. Pushes container image to GitHub Container Registry (`ghcr.io`).

---

## Traditional Production Deployment (Manual Ubuntu / Systemd)


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
