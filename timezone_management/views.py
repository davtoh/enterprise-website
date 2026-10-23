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

# https://docs.djangoproject.com/en/2.0/topics/i18n/timezones/#selecting-the-current-time-zone


def get_all_timezones():
    if available_timezones is not None:
        return sorted(available_timezones())
    if pytz is not None:
        return pytz.common_timezones
    return ['UTC', 'America/Bogota', 'America/New_York', 'Europe/London', 'Europe/Paris', 'Asia/Tokyo']


def set_timezone(request):
    if request.method == 'POST':
        request.session['django_timezone'] = request.POST.get('timezone', 'UTC')
        return redirect(request.POST.get('next', '/'))
    else:
        return render(request, 'timezone_management/select.html', {'timezones': get_all_timezones()})


