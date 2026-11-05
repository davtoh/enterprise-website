"""
Integrations configuration for enterprise_website project.

Includes Logging, REST Framework, Email, Celery tasks, and
Intelligent Tracker Edge AI microservice configuration.
"""

import os
import sys
from enterprise_website.settings.base import KEYS, TIME_ZONE
from enterprise_website.settings.storage import REDIS_URL

# for testing mailing
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = 'localhost'
EMAIL_PORT = '1025'

# logging  https://docs.djangoproject.com/en/dev/topics/logging/
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'filters': {
        #'special': {
        #    '()': 'project.logging.SpecialFilter',
        #    'foo': 'bar',
        #},
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'console':{
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': [], #['special']
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
    }
}

# django-rest-framework
REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],
    # allows you to control how many objects per page are returned
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}

# Celery Configuration
# https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_ALWAYS_EAGER = (
    os.getenv("CELERY_TASK_ALWAYS_EAGER", "False").lower() in ("true", "1", "t")
    or "pytest" in sys.modules
    or "test" in sys.argv
)
CELERY_TASK_EAGER_PROPAGATES = True

# Periodic Celery Beat Scheduled Tasks
CELERY_BEAT_SCHEDULE = {
    'crm_process_email_sequences': {
        'task': 'crm.process_email_sequences',
        'schedule': 300.0,  # every 5 minutes
    },
    'erp_check_low_stock_alerts': {
        'task': 'erp.check_low_stock_alerts',
        'schedule': 3600.0,  # every hour
    },
}

# Intelligent Tracker Edge AI Microservice Integration
INTELLIGENT_TRACKER_SECRET_KEY = os.getenv(
    "INTELLIGENT_TRACKER_SECRET_KEY",
    KEYS.get("INTELLIGENT_TRACKER_SECRET_KEY", "tracker-secret-key-change-in-production-hmac-sha256"),
)

