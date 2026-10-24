import uuid
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import ListView, DetailView
from .models import TaskJob
from .tasks import run_auto_translate, run_collectstatic, run_external_script


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restricts view access to staff members."""

    def test_func(self):
        return self.request.user.is_active and self.request.user.is_staff


class TaskJobListView(StaffRequiredMixin, ListView):
    """Displays a list of all background task jobs with filter and status indicators."""

    model = TaskJob
    template_name = "task_runner/job_list.html"
    context_object_name = "jobs"
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(name__icontains=query) | qs.filter(task_id__icontains=query)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_status"] = self.request.GET.get("status", "")
        context["search_query"] = self.request.GET.get("q", "")
        context["status_choices"] = TaskJob.Status.choices
        return context


class TaskJobDetailView(StaffRequiredMixin, DetailView):
    """Detailed view for an individual task job displaying metadata and live widget."""

    model = TaskJob
    template_name = "task_runner/job_detail.html"
    context_object_name = "job"

    def get_object(self, queryset=None):
        task_id = self.kwargs.get("task_id")
        return get_object_or_404(TaskJob, task_id=task_id)


class TaskJobStatusAPIView(View):
    """JSON status endpoint for polling fallbacks and programmatic status queries."""

    def get(self, request, task_id, *args, **kwargs):
        job = TaskJob.objects.filter(task_id=task_id).first()
        if not job:
            return JsonResponse({"error": _("Task not found")}, status=404)
        return JsonResponse(job.to_dict())


class TaskTriggerView(StaffRequiredMixin, View):
    """Triggers background Celery tasks from the web interface."""

    def post(self, request, *args, **kwargs):
        task_type = request.POST.get("task_type")
        task_id = str(uuid.uuid4())

        if task_type == "auto_translate":
            lang = request.POST.get("lang") or None
            backend = request.POST.get("backend", "mymemory")
            max_entries = request.POST.get("max_entries")
            max_val = int(max_entries) if max_entries and max_entries.isdigit() else None

            # Create pending TaskJob record
            TaskJob.objects.create(
                task_id=task_id,
                name=f"Auto-Translate ({lang or 'all'}, {backend})",
                status=TaskJob.Status.PENDING,
                created_by=request.user,
            )
            run_auto_translate.apply_async(
                kwargs={"lang": lang, "backend": backend, "max_entries": max_val},
                task_id=task_id,
            )
            messages.success(request, _("Auto-translate task queued successfully."))

        elif task_type == "collectstatic":
            TaskJob.objects.create(
                task_id=task_id,
                name="Collect Static Files",
                status=TaskJob.Status.PENDING,
                created_by=request.user,
            )
            run_collectstatic.apply_async(task_id=task_id)
            messages.success(request, _("Collectstatic task queued successfully."))

        elif task_type == "external_script":
            cmd = request.POST.get("command", "").strip()
            if not cmd:
                messages.error(request, _("Please provide a command to run."))
                return redirect("task_runner:list")

            TaskJob.objects.create(
                task_id=task_id,
                name=f"Script: {cmd[:30]}",
                status=TaskJob.Status.PENDING,
                created_by=request.user,
            )
            run_external_script.apply_async(args=[cmd], task_id=task_id)
            messages.success(request, _("External script queued successfully."))

        else:
            messages.error(request, _("Unknown task type specified."))
            return redirect("task_runner:list")

        return redirect("task_runner:detail", task_id=task_id)
