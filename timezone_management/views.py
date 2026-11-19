try:
    from zoneinfo import ZoneInfo, available_timezones
except ImportError:
    ZoneInfo = None
    available_timezones = None

try:
    import pytz
except ImportError:
    pytz = None

from django.shortcuts import redirect, render

from .models import TimeZone

# https://docs.djangoproject.com/en/2.0/topics/i18n/timezones/#selecting-the-current-time-zone


def get_all_timezones():
    if available_timezones is not None:
        return sorted(available_timezones())
    if pytz is not None:
        return pytz.common_timezones
    return ['UTC', 'America/Bogota', 'America/New_York', 'Europe/London', 'Europe/Paris', 'Asia/Tokyo']


def _is_valid_timezone(tz_name):
    if not tz_name or len(tz_name) > 35:
        return False
    if ZoneInfo is not None:
        try:
            ZoneInfo(tz_name)
            return True
        except Exception:
            pass
    if pytz is not None:
        try:
            pytz.timezone(tz_name)
            return True
        except Exception:
            pass
    return tz_name in get_all_timezones()


def set_timezone(request):
    if request.method == 'POST':
        tz_name = request.POST.get('timezone', 'UTC').strip() or 'UTC'
        request.session['django_timezone'] = tz_name
        if getattr(request, 'user', None) and request.user.is_authenticated and _is_valid_timezone(tz_name):
            tz_obj, _created = TimeZone.objects.get_or_create(timezone=tz_name)
            if request.user.timezone_id != tz_obj.pk:
                request.user.timezone = tz_obj
                request.user.save(update_fields=['timezone'])
        return redirect(request.POST.get('next', '/'))
    else:
        return render(request, 'timezone_management/select.html', {'timezones': get_all_timezones()})


