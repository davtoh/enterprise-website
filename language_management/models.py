from django.db import models
from django.forms import ModelForm
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class LayoutLanguages(models.Model):
    user_language = models.CharField(max_length=7, choices=settings.LANGUAGES)  # defaults supported


class LayoutLanguagesForm(ModelForm):
    class Meta:
        model = LayoutLanguages
        fields = ('user_language',)
        labels = {
            'user_language': _('User language'),
        }
        help_texts = {
            'user_language': _('Set the language to show in site'),
        }
        error_messages = {
            'user_language': {
                'max_length': _("This language code is too long."),
            },
        }
