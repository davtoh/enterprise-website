from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import ASCIIUsernameValidator
from timezone_management.models import TimeZone
from easy_timezones.signals import detected_timezone
from django.dispatch import receiver

# https://docs.djangoproject.com/en/2.0/ref/contrib/auth/
# http://django-book.readthedocs.io/en/latest/chapter14.html#using-users
# https://simpleisbetterthancomplex.com/tutorial/2018/01/29/how-to-implement-dependent-or-chained-dropdown-list-with-django.html
# https://simpleisbetterthancomplex.com/tutorial/2016/07/22/how-to-extend-django-user-model.html
# https://www.codingforentrepreneurs.com/blog/how-to-create-a-custom-django-user-model/
# https://wsvincent.com/django-user-authentication-tutorial-login-and-logout/
# https://wsvincent.com/django-custom-user-model-tutorial/


class Country(models.Model):
    name = models.CharField(max_length=30)

    def __str__(self):
        return self.name


class City(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    name = models.CharField(max_length=30)

    def __str__(self):
        return self.name


class Gender(models.Model):
    gender = models.CharField(max_length=200)

    def __str__(self):
        return self.gender


class SiteUser(AbstractUser):
    username_validator = ASCIIUsernameValidator()

    birthdate = models.DateField(null=True, blank=True)
    gender = models.ForeignKey(Gender, on_delete=models.CASCADE)
    picture = models.ImageField()
    timezone = models.ForeignKey(TimeZone, on_delete=models.SET_NULL, null=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True)

    # http://benlopatin.com/using-django-proxy-models/
    #class Meta:
    #    proxy = True  # If no new field is added.

    def __str__(self):
        return self.username


@receiver(detected_timezone, sender=SiteUser)
def process_timezone(sender, instance, timezone, **kwargs):
    if instance.timezone != timezone:
        instance.timezone = timezone
        instance.save()
