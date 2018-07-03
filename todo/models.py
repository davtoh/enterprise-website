from django.db import models
from datetime import datetime
from django.utils import timezone


class Todo(models.Model):
    # https://www.youtube.com/watch?v=2yXfUPwlZTw
    title = models.CharField(max_length=500)
    text = models.TextField()
    created_at = models.DateTimeField(default=timezone.now, blank=True)

    def __str__(self):
        # show title in the list of Todo's
        return self.title

