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


class Location(models.Model):
    name = models.CharField(_('location name'), help_text=_('Facility, campus, or site name (e.g. North HQ)'), max_length=255)
    code = models.CharField(_('location code'), help_text=_('Unique site identifier (e.g. SITE-NORTH-01)'), max_length=50, unique=True)
    city = models.ForeignKey(Cities, verbose_name=_('city'), help_text=_('City location'), on_delete=models.SET_NULL, null=True, blank=True)
    address = models.CharField(_('address'), help_text=_('Street address'), max_length=255, blank=True)
    latitude = models.DecimalField(_('latitude'), help_text=_('Site latitude coordinate'), max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(_('longitude'), help_text=_('Site longitude coordinate'), max_digits=11, decimal_places=8, null=True, blank=True)
    is_active = models.BooleanField(_('is active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _('location')
        verbose_name_plural = _('locations')

    def __str__(self):
        return f"{self.name} ({self.code})"