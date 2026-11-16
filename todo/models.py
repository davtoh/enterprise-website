from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ActionItemStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    IN_PROGRESS = "in_progress", _("In Progress")
    DONE = "done", _("Done")
    CANCELLED = "cancelled", _("Cancelled")


class Todo(models.Model):
    # https://www.youtube.com/watch?v=2yXfUPwlZTw
    title = models.CharField(_("Title"), max_length=500)
    text = models.TextField(_("Text"))
    created_at = models.DateTimeField(_("Created at"), default=timezone.now, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="action_items",
        verbose_name=_("Owner"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=ActionItemStatus.choices,
        default=ActionItemStatus.PENDING,
    )
    due_date = models.DateField(_("Due date"), null=True, blank=True)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Related content type"),
    )
    object_id = models.PositiveIntegerField(_("Related object ID"), null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        verbose_name = _("Action Item")
        verbose_name_plural = _("Action Items")

    def __str__(self):
        # show title in the list of Todo's
        return self.title


ActionItem = Todo

