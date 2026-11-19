from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.utils.translation import gettext as _

from .models import ActionItemStatus, Todo

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
    todos = Todo.objects.select_related('owner', 'content_type').all()
    status_filter = request.GET.get('status', '').strip()
    if status_filter in ActionItemStatus.values:
        todos = todos.filter(status=status_filter)

    owner_filter = request.GET.get('owner', '').strip()
    if owner_filter == 'me' and request.user.is_authenticated:
        todos = todos.filter(owner=request.user)
    elif owner_filter.isdigit():
        todos = todos.filter(owner_id=int(owner_filter))

    context = {
        'name': 'User',
        'todos': todos,
        'statuses': ActionItemStatus.choices,
        'current_status': status_filter,
        'current_owner': owner_filter,
    }
    return render(request, 'todo/index.html', context=context)


def details(request, id):
    # get data - using get_object_or_404 to avoid unhandled 500 exceptions
    todo = get_object_or_404(Todo.objects.select_related('owner', 'content_type'), id=id)

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


def _resolve_todo_owner(request):
    owner_param = request.POST.get('owner', '').strip()
    if owner_param.isdigit():
        return get_user_model().objects.filter(pk=int(owner_param)).first()
    if request.user.is_authenticated:
        return request.user
    return None


def add(request):
    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        text = request.POST.get('text', '').strip()
        status_val = request.POST.get('status', ActionItemStatus.PENDING).strip()
        if status_val not in ActionItemStatus.values:
            status_val = ActionItemStatus.PENDING
        due_date_val = parse_date(request.POST.get('due_date', '').strip())

        if not title:
            messages.error(request, _('Todo title cannot be empty.'), extra_tags='danger')
            return render(request, 'todo/add.html', {'text': text, 'statuses': ActionItemStatus.choices})

        todo = Todo(
            title=title,
            text=text,
            status=status_val,
            due_date=due_date_val,
            owner=_resolve_todo_owner(request),
        )
        todo.save()
        # using next convention https://stackoverflow.com/a/35796559/5288758
        messages.success(request, _('Task created successfully!'), extra_tags='alert')
        return redirect(request.POST.get('next', 'todo:index'))
    return render(request, 'todo/add.html', {'statuses': ActionItemStatus.choices})


def delete(request, id):
    todo = get_object_or_404(Todo, id=id)
    todo.delete()
    if request.headers.get('HX-Request'):
        return HttpResponse("", status=200)
    messages.success(request, _('Task deleted successfully!'), extra_tags='alert')
    return redirect('todo:index')

