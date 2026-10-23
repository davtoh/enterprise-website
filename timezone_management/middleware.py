try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

try:
    import pytz
except ImportError:
    pytz = None

from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class TimezoneMiddleware(MiddlewareMixin):
    def process_request(self, request):
        tzname = request.session.get('django_timezone')
        if tzname:
            if ZoneInfo is not None:
                try:
                    timezone.activate(ZoneInfo(tzname))
                    return
                except Exception:
                    pass
            if pytz is not None:
                try:
                    timezone.activate(pytz.timezone(tzname))
                    return
                except Exception:
                    pass
            try:
                timezone.activate(tzname)
            except Exception:
                timezone.deactivate()
        else:
            timezone.deactivate()