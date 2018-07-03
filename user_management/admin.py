from django.contrib import admin
#from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from .forms import SiteUserCreationForm, SiteUserChangeForm
from .models import SiteUser


class SiteUserAdmin(UserAdmin):
    add_form = SiteUserCreationForm
    form = SiteUserChangeForm
    model = SiteUser
    list_display = ['email', 'username', 'first_name', 'last_name']


admin.site.register(SiteUser, SiteUserAdmin)
