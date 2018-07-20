from django.contrib import admin
#from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from .forms import SiteUserCreationForm, SiteUserChangeForm
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class SiteUserAdmin(UserAdmin):
    add_form = SiteUserCreationForm
    form = SiteUserChangeForm
    model = settings.AUTH_USER_MODEL
    #list_display = ['username', 'email', 'first_name', 'last_name']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'date_of_birth', 'country', 'city', 'gender', 'timezone', 'profile_picture')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
    )


admin.site.register(settings.AUTH_USER_MODEL, SiteUserAdmin)
