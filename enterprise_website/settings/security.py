"""
Security, Authentication, and Production Hardening configuration for enterprise_website project.

https://docs.djangoproject.com/en/5.0/topics/security/
https://docs.djangoproject.com/en/5.0/ref/middleware/#module-django.middleware.security
"""

import os
from enterprise_website.settings.base import DEBUG

# login
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/accounts/login'  # must be absolute path
AUTH_USER_MODEL = 'user_management.SiteUser'

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Security & Production Hardening
X_FRAME_OPTIONS = os.getenv("X_FRAME_OPTIONS", "DENY")
SECURE_CONTENT_TYPE_NOSNIFF = True

# CSRF Trusted Origins (Required for Django 4.0+ when running behind reverse proxies or on non-standard ports)
# https://docs.djangoproject.com/en/5.0/ref/settings/#csrf-trusted-origins
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

if not DEBUG:
    # Production HTTPS & Cookie Security
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() in ("true", "1", "t")
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "True").lower() in ("true", "1", "t")
    CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "True").lower() in ("true", "1", "t")

    # HTTP Strict Transport Security (HSTS)
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "True").lower() in ("true", "1", "t")
    SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "True").lower() in ("true", "1", "t")

    # Reverse proxy SSL termination (Nginx, Traefik, AWS ALB)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False

