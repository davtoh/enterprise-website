from django.shortcuts import redirect, render

# https://docs.djangoproject.com/en/2.0/topics/i18n/timezones/#selecting-the-current-time-zone


def set_timezone(request):
    if request.method == 'POST':
        request.session['django_timezone'] = request.POST['timezone']
        return redirect('/')
    else:
        return render(request, 'template.html', {'timezones': pytz.common_timezones})
