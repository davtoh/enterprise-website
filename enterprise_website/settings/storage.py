"""
Storage, Database, and Static/Media files configuration for enterprise_website project.
"""

import os
import sys
from enterprise_website.settings.base import BASE_DIR, KEYS

# Database - OS-agnostic: SQLite for zero-setup local dev; MySQL/Postgres in prod
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases
USE_SQLITE = os.getenv("USE_SQLITE", "True").lower() in ("true", "1", "t")

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': os.getenv('DB_ENGINE', ''),
            'NAME': os.getenv('DB_NAME', KEYS.get('DB_NAME', '')),
            'USER': os.getenv('DB_USER', KEYS.get('DB_USER', '')),
            'PASSWORD': os.getenv('DB_PASSWORD', KEYS.get('DB_PASS', '')),
            'HOST': os.getenv('DB_HOST', ''),
            'PORT': os.getenv('DB_PORT', ''),
        }
    }

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

MEDIA_URL = os.getenv('MEDIA_URL', '/media-files/')
MEDIA_ROOT = BASE_DIR / 'media'

# Channels Layer configuration (Redis for IPC between Celery and Daphne/Web, with InMemory fallback for tests)
TESTING = "pytest" in sys.modules or "test" in sys.argv
REDIS_URL = os.getenv("REDIS_URL", "")
USE_REDIS_CHANNEL_LAYER = os.getenv("USE_REDIS_CHANNEL_LAYER", "True").lower() in ("true", "1", "t") and not TESTING

if USE_REDIS_CHANNEL_LAYER and REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [REDIS_URL],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }

