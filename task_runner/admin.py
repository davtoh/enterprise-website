import uuid
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _, gettext
from .models import TaskJob
from .tasks import run_auto_translate, run_collectstatic, run_external_script


@admin.register(TaskJob)
class TaskJobAdmin(admin.ModelAdmin):
    change_list_template = "admin/task_runner/taskjob/change_list.html"

    list_display = (
        "name",
        "task_id_short",
        "status_badge",
        "progress_bar",
        "created_by",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("task_id", "name", "log_output", "error_message")
    readonly_fields = (
        "task_id",
        "created_at",
        "updated_at",
        "result_data",
        "error_message",
        "live_widget",
    )
    fieldsets = (
        (
            _("Task Overview"),
            {
                "fields": (
                    "name",
                    "task_id",
                    "status",
                    "progress",
                    "created_by",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        (
            _("Live Monitoring"),
            {
                "fields": ("live_widget",),
            },
        ),
        (
            _("Task Logs & Result"),
            {
                "classes": ("collapse",),
                "fields": ("result_data", "error_message", "log_output"),
            },
        ),
    )
    actions = [
        "action_run_collectstatic",
        "action_run_auto_translate_es",
        "action_run_external_script",
    ]

    @admin.display(description=_("Task ID"))
    def task_id_short(self, obj):
        return f"{obj.task_id[:8]}..."

    @admin.display(description=_("Status"))
    def status_badge(self, obj):
        colors = {
            "RUNNING": "primary",
            "SUCCESS": "success",
            "FAILURE": "danger",
            "REVOKED": "warning",
            "PENDING": "secondary",
        }
        color = colors.get(obj.status, "secondary")
        return format_html(
            '<span style="padding: 3px 8px; border-radius: 4px; font-weight: bold; color: white; background-color: var(--bs-{0}, #{1});">{2}</span>',
            color,
            "0d6efd" if color == "primary" else ("198754" if color == "success" else ("dc3545" if color == "danger" else "6c757d")),
            obj.status,
        )

    @admin.display(description=_("Progress"))
    def progress_bar(self, obj):
        return format_html(
            '<div style="width: 120px; background: #e9ecef; border-radius: 4px; overflow: hidden; height: 14px;">'
            '<div style="width: {0}%; background: #0d6efd; height: 100%; text-align: center; font-size: 10px; color: white; line-height: 14px;">{0}%</div>'
            '</div>',
            obj.progress,
        )

    @admin.display(description=_("Real-time Task Monitor"))
    def live_widget(self, obj):
        if not obj.pk:
            return _("Save task first to display live stream.")
        from django.template.loader import render_to_string
        return mark_safe(
            render_to_string(
                "task_runner/task_progress_widget.html",
                {
                    "task_id": obj.task_id,
                    "title": obj.name,
                    "status": obj.status,
                    "progress": obj.progress,
                    "log_output": obj.log_output,
                    "error_message": obj.error_message,
                    "auto_connect": True,
                },
            )
        )

    @admin.action(description=_("Trigger Collectstatic in background"))
    def action_run_collectstatic(self, request, queryset):
        run_collectstatic.delay()
        self.message_user(request, _("Background collectstatic task queued."))

    @admin.action(description=_("Trigger Auto-Translate (Spanish baseline)"))
    def action_run_auto_translate_es(self, request, queryset):
        run_auto_translate.delay(lang="es", max_entries=5)
        self.message_user(request, _("Background auto-translate task for Spanish queued."))

    @admin.action(description=_("Launch External Script"))
    def action_run_external_script(self, request, queryset):
        return redirect("admin:task_runner_launch_script")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "launch-script/",
                self.admin_site.admin_view(self.launch_script_view),
                name="task_runner_launch_script",
            ),
        ]
        return custom_urls + urls

    def launch_script_view(self, request):
        """Custom Django Admin view to queue external scripts directly with live streaming."""
        if request.method == "POST":
            cmd = request.POST.get("command", "").strip()
            if not cmd:
                self.message_user(request, _("Please provide a valid command."), level=messages.ERROR)
                return render(request, "admin/task_runner/taskjob/launch_script.html")

            task_id = str(uuid.uuid4())
            job = TaskJob.objects.create(
                task_id=task_id,
                name=f"Admin Script: {cmd[:40]}",
                status=TaskJob.Status.PENDING,
                created_by=request.user if request.user.is_authenticated else None,
            )
            run_external_script.apply_async(args=[cmd], task_id=task_id)
            self.message_user(
                request,
                _("External script '{0}' queued successfully with Task ID: {1}").format(cmd, task_id),
                level=messages.SUCCESS,
            )
            return redirect("admin:task_runner_taskjob_change", job.pk)

        return render(
            request,
            "admin/task_runner/taskjob/launch_script.html",
            {
                "title": _("Launch External Script"),
                "opts": self.model._meta,
                "has_view_permission": self.has_view_permission(request),
            },
        )
