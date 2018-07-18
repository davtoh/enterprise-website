from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.admin.widgets import AdminDateWidget
from .models import SiteUser, Cities, States
from django.core.files.images import get_image_dimensions
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
import datetime
from dateutil.relativedelta import relativedelta


def years_ago(years, from_date=None):
    # https://stackoverflow.com/a/765990/5288758
    if from_date is None:
        from_date = datetime.date.today()
    return from_date - relativedelta(years=years)


class SiteUserCommonForm:

    def clean_profile_picture(self):
        # https://stackoverflow.com/a/6396744/5288758

        avatar = self.cleaned_data['profile_picture']
        if avatar is None:
            return

        try:
            w, h = get_image_dimensions(avatar)

            #validate dimensions
            max_width = max_height = 100
            if w > max_width or h > max_height:
                raise forms.ValidationError(_('Please use an image that is '
                     '%(w) x %(h) pixels or smaller.') % {"w": max_width, "h": max_height})

            #validate content type
            main, sub = avatar.content_type.split('/')
            if not (main == 'image' and sub in ['jpeg', 'pjpeg', 'gif', 'png']):
                raise forms.ValidationError(_(u'Please use a JPEG, GIF or PNG image.'))

            #validate file size
            max_size = 20
            if len(avatar) > (max_size * 1024):
                max_size_str = "20k".format(max_size)
                raise forms.ValidationError(_('Avatar file size may not exceed %s.') % max_size_str)

        except AttributeError:
            """
            Handles case when we are updating the user profile
            and do not supply a new avatar
            """
            pass

        return avatar

    def clean_date_of_birth(self):
        data = self.cleaned_data['date_of_birth']

        # Check date is not in future
        if data > datetime.date.today():
            raise ValidationError(_('Invalid date - unless you come from the future'))

        # Check date is in legal range
        legal_age = 18
        if data > years_ago(legal_age):
            raise ValidationError(_('Invalid date - you must older than %d') % legal_age)

        # Remember to always return the cleaned data.
        return data


class SiteUserCreationForm(UserCreationForm, SiteUserCommonForm):

    class Meta(UserCreationForm.Meta):
        model = SiteUser
        fields = ('username', 'first_name', 'last_name', 'email', 'phone_number', 'profile_picture', 'date_of_birth', 'country', 'state', 'city')
        # https://stackoverflow.com/a/22250192/5288758
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'class':'datepicker'}),  # https://stackoverflow.com/a/5455164/5288758
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['city'].queryset = Cities.objects.none()
        self.fields['state'].queryset = States.objects.none()

        if 'country' in self.data:
            try:
                country_id = int(self.data.get('country'))
                self.fields['state'].queryset = States.objects.filter(country_id=country_id).order_by('name')
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty State queryset
        elif self.instance.pk:
            # form is being used to update an existing user
            self.fields['state'].queryset = self.instance.country.states.order_by('name')

        if 'state' in self.data and 'country' in self.data:
            try:
                state_id = int(self.data.get('state'))
                country_id = int(self.data.get('country'))
                self.fields['city'].queryset = Cities.objects.filter(state_id=state_id, country_id=country_id).order_by('name')
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty City queryset
        elif self.instance.country is not None:
            # form is being used to update an existing user
            self.fields['city'].queryset = self.instance.state.cities.order_by('name')


class SiteUserChangeForm(UserChangeForm, SiteUserCommonForm):

    class Meta:
        model = SiteUser
        fields = UserChangeForm.Meta.fields


class ImageUploadForm(forms.Form):
    """Image upload form."""
    image = forms.ImageField()
