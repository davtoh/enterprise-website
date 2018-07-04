import pytz
from django.db import models
from django.forms import ModelForm
from timezone_field import TimeZoneField
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from collections import defaultdict


def _get_groups(tags, compact='others', original=False):
    """

    :param tags:
    :param compact:
    :param original:
    :return: dictionary with continets as keys and conutries as values
    """
    res = defaultdict(list)
    for tag in tags:
        sep = tag.split('/')
        if len(sep) > 1:
            if original:
                res[sep[0]].append(tag)
            else:
                res[sep[0]].append(sep[1])
        elif compact:
            res[compact].append(sep[0])
        else:
            res[sep[0]].append(sep[0])
    return res


show_timezones = pytz.all_timezones  # pytz.common_timezones


class TimeZone(models.Model):
    time_zones = [(i, _(i)) for i in show_timezones]
    time_zone_groups = [(_(k), [(t if '/' not in t else k+'/'+t, _(t)) for t in v]) for k, v in _get_groups(show_timezones).items()]
    # FIXME groups not supported in TimeZoneField
    #timezone = TimeZoneField(choices=time_zone_groups, max_length=35, default=settings.TIME_ZONE)  # defaults supported
    timezone = models.CharField(choices=time_zone_groups, max_length=35, default=settings.TIME_ZONE)


class TimeZoneForm(ModelForm):
    class Meta:
        model = TimeZone
        fields = ('timezone',)
        labels = {
            'timezone': _('Sets the timezone'),
        }
        help_texts = {
            'timezone': _('Select the timezone to keep track of time'),
        }
        error_messages = {
            'timezone': {
                'max_length': _("This timezone format is too long"),
            },
        }
