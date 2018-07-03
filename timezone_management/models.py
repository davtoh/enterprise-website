import pytz
from django.db import models
from django.forms import ModelForm
from timezone_field import TimeZoneField
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from collections import defaultdict


def _get_groups(tags, compact='others', original=False):
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


class TimeZone(models.Model):
    time_zones = [(i, _(i)) for i in pytz.all_timezones]
    time_zone_groups = [(_(k), (v if '/' not in v else k+'/'+v, _(v))) for k, v in _get_groups(pytz.all_timezones).items()]
    timezone = TimeZoneField(choices=time_zone_groups, max_length=35, default=settings.TIME_ZONE)  # defaults supported
    #timezone = models.CharField(choices=[(x, x) for x in pytz.common_timezones], max_length=35, default=settings.TIME_ZONE)


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
