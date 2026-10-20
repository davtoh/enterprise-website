# Enterprise Website

A modular enterprise web portal built with **Django 5.0**, **Channels / Daphne** (WebSockets/ASGI), **Django REST Framework**, and **Django-Allauth**. Designed to be completely OS-agnostic (runs on Linux, macOS, and Windows) with zero setup required for local development.

---

## Features
- **Modern Django Stack:** Powered by Django 5.0 & Python 3.12.
- **Cross-Platform & OS-Agnostic:** Runs seamlessly on Windows, Linux, and macOS without machine-dependent hardcoded configurations.
- **Zero-Barrier Local Development:** Out-of-the-box local SQLite database mode (no MySQL or C++ compiler required).
- **Production-Ready Database Support:** Switch seamlessly to MySQL or PostgreSQL using `.env` environment variables.
- **Authentication & User Management:** Custom user models, Google OAuth2 social login via `django-allauth`, international phone number validation, and country pickers.
- **Internationalization (i18n):** Multi-language support with `django-rosetta`.
- **Async Capabilities:** ASGI ready with Channels & Daphne.

---

## Quickstart Guide

### 1. Prerequisites
- **Python 3.12** (or Python >= 3.10)
- Git

---

### 2. Setup Virtual Environment

#### On Windows (PowerShell):
```powershell
# Clone the repository (if not already cloned)
git clone https://github.com/davtoh/enterprise-website.git
cd enterprise-website

# Create and activate virtual environment
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

#### On Linux / macOS (bash / zsh):
```bash
# Clone the repository
git clone https://github.com/davtoh/enterprise-website.git
cd enterprise-website

# Create and activate virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### 3. Environment Configuration

Copy the sample environment file:
```bash
# Windows
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
This allows the application to run immediately on any platform without configuring an external database.

---

### 4. Database Setup & Migrations

Run database migrations:
```bash
python manage.py migrate
```

(Optional) Create a superuser for administration:
```bash
python manage.py createsuperuser
```

---

### 5. Running the Application

Start the development server:
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

- Admin Panel: `http://127.0.0.1:8000/admin/`
- REST API: `http://127.0.0.1:8000/rest_api/`
- Rosetta Translations: `http://127.0.0.1:8000/rosetta/`

---

## Production Deployment (MySQL / PostgreSQL)

For production environments, update `.env`:
```ini
DEBUG=False
SECRET_KEY=your-strong-production-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
USE_SQLITE=False
DB_ENGINE=django.db.backends.mysql
DB_NAME=productsDB
DB_USER=production_user
DB_PASSWORD=production_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

Install production packages:
```bash
pip install -r requirements/production.txt
```

Run with Daphne (ASGI):
```bash
daphne -b 0.0.0.0 -p 8000 enterprise_website.asgi:application
```
