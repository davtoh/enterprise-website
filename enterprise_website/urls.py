"""enterprise_website URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage
from django.conf.urls.static import static  # https://docs.djangoproject.com/en/2.0/howto/static-files/
from timezone_management import views as tz_views
from language_management.views import set_language_and_sync_profile
from plugin_registry.admin_views import PluginMarketplaceView
from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

urlpatterns = [
    path('', include('home.urls')),
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url("favicon.ico"))),
    path('todo/', include('todo.urls')),
    path('polls/', include('polls.urls')),
    path('webprogram/', include('webprogram.urls')),
    path('lang/', include('language_management.urls')),
    path('tz/', include('timezone_management.urls')),
    path('tz/set/', tz_views.set_timezone, name='set_timezone'),
    path('accounts/', include('user_management.urls')),
    path('tasks/', include('task_runner.urls')),
    path('theme/', include('theme_management.urls')),
    path('media/', include('video_gallery.urls')),
    path('videos/', RedirectView.as_view(url='/media/', permanent=False)),
    path('crm/', include('crm.urls')),
    path('erp/', include('erp.urls')),
    path('security/', include('intelligent_tracker_hub.urls')),
    path('api/v1/', include('rest_api.v1_urls')),

    #path('accounts/', include('django.contrib.auth.urls')),
    path(
        'admin/marketplace/',
        admin.site.admin_view(PluginMarketplaceView.as_view()),
        name='admin_marketplace',
    ),
    path('admin/', admin.site.urls),
    path('cms/', include(wagtailadmin_urls)),
    path('documents/', include(wagtaildocs_urls)),
    path('i18n/setlang/', set_language_and_sync_profile, name='set_language'),
    path('i18n/', include('django.conf.urls.i18n')),  # <url path>/setlang
    path('rest_api/', include('rest_api.urls')),  # , namespace='rest_framework'
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += [
        path('rosetta/', include('rosetta.urls'))
    ]

# Wagtail catch-all page serving (must remain after explicit Django routes)
urlpatterns += [
    path('', include(wagtail_urls)),
]

# Change admin site title
# https://matheusho.svbtle.com/change-django-admin-site-title
#from django.utils.translation import ugettext_lazy as _
#admin.site.site_header = _("Site Administration")
#admin.site.site_title = _("My Site Admin")