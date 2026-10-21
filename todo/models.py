from django.db import models
from datetime import datetime
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Todo(models.Model):
    # https://www.youtube.com/watch?v=2yXfUPwlZTw
    title = models.CharField(_("Title"), max_length=500)
    text = models.TextField(_("Text"))
    created_at = models.DateTimeField(_("Created at"), default=timezone.now, blank=True)

    class Meta:
        verbose_name = _("Todo")
        verbose_name_plural = _("Todos")

    def __str__(self):
        # show title in the list of Todo's
        return self.title

