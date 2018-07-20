from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import ASCIIUsernameValidator
from timezone_management.models import TimeZone
from easy_timezones.signals import detected_timezone
from django.dispatch import receiver
from location_management.models import Countries, States, Cities
from phonenumber_field.modelfields import PhoneNumberField
from django.conf import settings

# https://docs.djangoproject.com/en/2.0/ref/contrib/auth/
# explains official user models https://docs.djangoproject.com/en/2.0/topics/auth/customizing/
# Sessions, Users, and Registration http://django-book.readthedocs.io/en/latest/chapter14.html#using-users
# custom user email-based https://www.codingforentrepreneurs.com/blog/how-to-create-a-custom-django-user-model/
# ways to extend user https://simpleisbetterthancomplex.com/tutorial/2016/07/22/how-to-extend-django-user-model.html
# ways to implement user  https://simpleisbetterthancomplex.com/tutorial/2018/01/18/how-to-implement-multiple-user-types-with-django.html
# custom user app 2017 https://wsvincent.com/django-user-authentication-tutorial-login-and-logout/
# custom user app 2018 https://wsvincent.com/django-custom-user-model-tutorial/
# sign up using social networks https://wsvincent.com/django-allauth-tutorial-custom-user-model/


class Gender(models.Model):
    gender = models.CharField(max_length=200)

    def __str__(self):
        return self.gender


class SiteUser(AbstractUser):
    """
    User Model for the site. This model can be used int the settings.py with
    AUTH_USER_MODEL = SiteUser.

    .. note::

        All user models can be accessed statically with settings.AUTH_USER_MODEL
        and dynamically with django.contrib.auth.get_user_model()
    """
    username_validator = ASCIIUsernameValidator()

    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.ForeignKey(Gender, on_delete=models.CASCADE, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/',
                                        #default='profile_pictures/None/no-img.jpg',
                                        blank=True, null=True)
    timezone = models.ForeignKey(TimeZone, on_delete=models.SET_NULL, null=True, blank=True)
    country = models.ForeignKey(Countries, on_delete=models.SET_NULL, null=True, blank=True)
    state = models.ForeignKey(States, on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey(Cities, on_delete=models.SET_NULL, null=True, blank=True)
    phone_number = PhoneNumberField(null=True, blank=True)  # https://stackoverflow.com/a/19131360/5288758

    # http://benlopatin.com/using-django-proxy-models/
    #class Meta:
    #    proxy = True  # If no new field is added.

    # USERNAME_FIELD = 'username'
    # REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username


@receiver(detected_timezone, sender=settings.AUTH_USER_MODEL)
def process_timezone(sender, instance, timezone, **kwargs):
    try:
        instance.timezone
    except AttributeError:
        return  # anonymous user

    user_choice = True
    update_choice = False

    # if user wants to always update his timezone
    if update_choice and instance.timezone != timezone:
        instance.timezone = timezone
        instance.save()

    # if user choice come first regardless of detected timezone
    if user_choice and instance.timezone and instance.timezone != timezone:
        from django.utils import timezone
        import pytz
        timezone.activate(pytz.timezone(instance.timezone))
