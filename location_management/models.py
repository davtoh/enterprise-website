from django.db import models
from django.utils.translation import gettext_lazy as _

# https://simpleisbetterthancomplex.com/tutorial/2018/01/29/how-to-implement-dependent-or-chained-dropdown-list-with-django.html


class Countries(models.Model):
    name = models.CharField(_('country name'), help_text=_('This is the help text'), max_length=255)
    code = models.CharField(_('country code'), help_text=_('This is the help text'), max_length=10)

    class Meta:
        ordering = ["name"]
        verbose_name = _('country')
        verbose_name_plural = _('countries')

    def __str__(self):
        return self.name


class States(models.Model):
    country = models.ForeignKey(Countries, verbose_name=_('country'), help_text=_('This is the help text'), on_delete=models.CASCADE)
    name = models.CharField(_('state name'), help_text=_('This is the help text'), max_length=255)
    code = models.CharField(_('state code'), help_text=_('This is the help text'), max_length=10)

    class Meta:
        ordering = ["name"]
        verbose_name = _('state')
        verbose_name_plural = _('states')

    def __str__(self):
        return self.name


class Cities(models.Model):
    country = models.ForeignKey(Countries, verbose_name=_('country'), help_text=_('This is the help text'), on_delete=models.CASCADE)
    state = models.ForeignKey(States, verbose_name=_('state'), help_text=_('This is the help text'), on_delete=models.CASCADE)
    name = models.CharField(_('city name'), help_text=_('This is the help text'), max_length=255)
    latitude = models.DecimalField(_('latitude'), help_text=_('This is the help text'), max_digits=10, decimal_places=8)
    longitude = models.DecimalField(_('longitude'), help_text=_('This is the help text'), max_digits=11, decimal_places=8)

    class Meta:
        ordering = ["name"]
        verbose_name = _('city')
        verbose_name_plural = _('cities')

    def __str__(self):
        return self.name