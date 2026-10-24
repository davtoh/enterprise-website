from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TaskRunnerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'task_runner'
    verbose_name = _('Background Task Runner')
