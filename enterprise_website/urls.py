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

# for the rest API
from django.contrib.auth import get_user_model
from rest_framework import routers, serializers, viewsets

urlpatterns = [
    path('', include('home.urls')),
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url("favicon.ico"))),
    path('todo/', include('todo.urls')),
    path('polls/', include('polls.urls')),
    path('webprogram/', include('webprogram.urls')),
    path('lang/', include('language_management.urls')),
    path('accounts/', include('user_management.urls')),
    #path('accounts/', include('django.contrib.auth.urls')),
    path('admin/', admin.site.urls),
    #path('admin2/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),  # <url path>/setlang
    path('rest_api/', include('rest_api.urls')),  # , namespace='rest_framework'
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += [
        path('rosetta/', include('rosetta.urls'))
    ]

# Change admin site title
# https://matheusho.svbtle.com/change-django-admin-site-title
#from django.utils.translation import ugettext_lazy as _
#admin.site.site_header = _("Site Administration")
#admin.site.site_title = _("My Site Admin")