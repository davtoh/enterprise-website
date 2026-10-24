import json
import logging
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


class TaskJob(models.Model):
    """
    Tracks lifecycle, progress percentage, logs, and status of Celery background jobs.
    Broadcasts real-time events to connected WebSocket clients via Django Channels.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        RUNNING = "RUNNING", _("Running")
        SUCCESS = "SUCCESS", _("Success")
        FAILURE = "FAILURE", _("Failure")
        REVOKED = "REVOKED", _("Revoked")

    task_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        verbose_name=_("Task ID"),
        help_text=_("Celery task UUID or unique identifier"),
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_("Task Name"),
        help_text=_("Human-readable name or task function path"),
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name=_("Status"),
    )
    progress = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Progress (%)"),
        help_text=_("Completion percentage between 0 and 100"),
    )
    log_output = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Log Output"),
        help_text=_("Captured stdout, stderr, or lifecycle log stream"),
    )
    error_message = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Error Message"),
        help_text=_("Exception message or stack trace if the task failed"),
    )
    result_data = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Result Data"),
        help_text=_("JSON-encoded output returned by the background task"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="task_jobs",
        verbose_name=_("Created By"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Background Task Job")
        verbose_name_plural = _("Background Task Jobs")

    def __str__(self):
        return f"{self.name} [{self.task_id[:8]}...] ({self.status} {self.progress}%)"

    def to_dict(self):
        """Returns JSON-serializable dictionary representation of the job."""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status,
            "progress": self.progress,
            "log_output": self.log_output,
            "error_message": self.error_message,
            "created_by": self.created_by.get_username() if self.created_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }

    def broadcast_update(self):
        """Broadcasts task update to the task's Django Channels WebSocket group."""
        try:
            channel_layer = get_channel_layer()
            if channel_layer is not None:
                group_name = f"task_{self.task_id}"
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        "type": "task_update",
                        "data": self.to_dict(),
                    },
                )
        except Exception as e:
            logger.debug("Failed to broadcast task update for %s: %s", self.task_id, e)

    def update_progress(self, percent: int, log_line: str = None, status: str = None, save: bool = True):
        """Updates progress percentage, appends optional log line, and broadcasts change."""
        self.progress = max(0, min(100, int(percent)))
        if status:
            self.status = status
        if log_line:
            clean_line = str(log_line).rstrip()
            if self.log_output:
                self.log_output += f"\n{clean_line}"
            else:
                self.log_output = clean_line

        if save:
            self.save(update_fields=["progress", "status", "log_output", "updated_at"])
            self.broadcast_update()

    def mark_started(self, log_line: str = None):
        """Marks task as RUNNING and emits initial running event."""
        self.status = self.Status.RUNNING
        if log_line:
            clean_line = str(log_line).rstrip()
            if self.log_output:
                self.log_output += f"\n{clean_line}"
            else:
                self.log_output = clean_line
        self.save(update_fields=["status", "log_output", "updated_at"])
        self.broadcast_update()

    def mark_success(self, result=None, log_line: str = None):
        """Marks task as SUCCESS, sets progress to 100%, records result, and broadcasts."""
        self.status = self.Status.SUCCESS
        self.progress = 100
        if result is not None:
            try:
                self.result_data = json.dumps(result, default=str)
            except Exception:
                self.result_data = str(result)
        if log_line:
            clean_line = str(log_line).rstrip()
            if self.log_output:
                self.log_output += f"\n{clean_line}"
            else:
                self.log_output = clean_line
        self.save(update_fields=["status", "progress", "result_data", "log_output", "updated_at"])
        self.broadcast_update()

    def mark_failure(self, error: str = None, traceback_str: str = None):
        """Marks task as FAILURE, records error message, and broadcasts."""
        self.status = self.Status.FAILURE
        if error:
            self.error_message = str(error)
        if traceback_str:
            clean_tb = str(traceback_str).rstrip()
            if self.log_output:
                self.log_output += f"\n[ERROR] {clean_tb}"
            else:
                self.log_output = f"[ERROR] {clean_tb}"
        elif error:
            if self.log_output:
                self.log_output += f"\n[ERROR] {error}"
            else:
                self.log_output = f"[ERROR] {error}"
        self.save(update_fields=["status", "error_message", "log_output", "updated_at"])
        self.broadcast_update()
