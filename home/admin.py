from django.contrib import admin
from django.utils.translation import gettext_lazy as _

admin.AdminSite.site_title = _("Page Administration")
admin.AdminSite.site_header = _("Administration")
