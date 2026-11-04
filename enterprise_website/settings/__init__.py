"""
Modular Django settings package for enterprise_website.

Aggregates configuration across domain-focused submodules:
  - base: Core Django paths, middleware, templates, i18n/l10n, rosetta
  - apps: Modular application registration (core, third-party, enterprise)
  - storage: SQLite/Postgres/MySQL databases, static/media assets, channels
  - security: User auth model, password validators, HTTPS/HSTS hardening
  - integrations: Logging, REST framework, Celery tasks, tracker secret
"""

from enterprise_website.settings.base import *
from enterprise_website.settings.apps import *
from enterprise_website.settings.storage import *
from enterprise_website.settings.security import *
from enterprise_website.settings.integrations import *

