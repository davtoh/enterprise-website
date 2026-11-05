"""
Installed applications configuration for enterprise_website project.

Application definition organized by core Django, third-party libraries,
and modular enterprise domain subsystems.
"""

DJANGO_CORE_APPS = [
    'daphne',  # Must be before django.contrib.staticfiles for channels/ASGI
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sites',
    'django.contrib.contenttypes',  # https://docs.djangoproject.com/en/2.0/ref/contrib/contenttypes/#module-django.contrib.contenttypes
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',  # https://docs.djangoproject.com/en/2.0/ref/contrib/staticfiles/#module-django.contrib.staticfiles
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    'rest_framework',  # support for rest apps
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'django_countries',  # https://github.com/SmileyChris/django-countries/
    'phonenumber_field',  # https://github.com/stefanfoulis/django-phonenumber-field
    'rosetta',
    'channels',
]

ENTERPRISE_APPS = [
    'plugin_registry.apps.PluginRegistryConfig',
    'menu_management.apps.MenuManagementConfig',
    'rest_api.apps.RestApiConfig',
    'webprogram.apps.WebprogramConfig',
    'home.apps.HomeConfig',
    'todo.apps.TodoConfig',
    'language_management.apps.LanguageManagementConfig',
    'polls.apps.PollsConfig',
    'custom_tags.apps.CustomTagsConfig',
    'location_management.apps.LocationManagementConfig',
    'user_management.apps.UserManagementConfig',
    'timezone_management.apps.TimezoneManagementConfig',
    'task_runner.apps.TaskRunnerConfig',
    'theme_management.apps.ThemeManagementConfig',
    'video_gallery.apps.VideoGalleryConfig',
    'crm.apps.CrmConfig',
    'erp.apps.ErpConfig',
    'intelligent_tracker_hub.apps.IntelligentTrackerHubConfig',
]

# Combined Application definition
INSTALLED_APPS = DJANGO_CORE_APPS + THIRD_PARTY_APPS + ENTERPRISE_APPS

