from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import SiteUser


class SiteUserCreationForm(UserCreationForm):

    class Meta(UserCreationForm.Meta):
        model = SiteUser
        fields = ('username', 'first_name', 'last_name', 'email', 'birthdate', 'country', 'city', 'password')


class SiteUserChangeForm(UserChangeForm):

    class Meta:
        model = SiteUser
        fields = UserChangeForm.Meta.fields