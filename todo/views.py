from django.shortcuts import render, redirect
from django.contrib import messages
#from django.http import HttpResponse, HttpResponseRedirect
#from django.urls import reverse
from .models import Todo
from django.urls import include
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None
    try:
        from pytz import timezone as ZoneInfo
    except ImportError:
        ZoneInfo = None


def index(request):
    # get data
    todos = Todo.objects.all()#[:10]

    # make context
    context = {
        'name': 'User',
        'todos': todos
    }
    return render(request, 'todo/index.html', context=context)


def details(request, id):
    # get data
    todo = Todo.objects.get(id=id)

    # make context
    detected_timezone = request.session.get('django_timezone')
    todo_date = todo.created_at
    if detected_timezone and ZoneInfo is not None:
        try:
            todo_date = todo.created_at.astimezone(ZoneInfo(detected_timezone))
        except Exception:
            pass

    context = {
        'todo': todo,
        'time_zone_user': detected_timezone,
        'date': todo_date,
    }
    return render(request, 'todo/details.html', context=context)


def add(request):
    if request.method == "POST":
        # get data
        title = request.POST['title']
        text = request.POST['text']

        # save to database
        todo = Todo(title=title, text=text)
        todo.save()
        # return redirect(request.META.get('HTTP_REFERER', 'todo:index')) # better do https://stackoverflow.com/a/35796559
        #return HttpResponseRedirect(reverse('todo:index'))
        # using next convention https://stackoverflow.com/a/35796559/5288758
        messages.success(request, 'Form submission successful', extra_tags='alert')
        return redirect(request.POST.get('next', 'todo:index'))
    else:
        return render(request, 'todo/add.html')
