import logging
import traceback
import uuid
from celery import Task
from .models import TaskJob

logger = logging.getLogger(__name__)


class TrackedTask(Task):
    """
    Celery Task base class that automatically syncs lifecycle events with a TaskJob model
    and streams real-time updates through Django Channels.
    """

    abstract = True

    def __call__(self, *args, **kwargs):
        task_id = self.request.id or str(uuid.uuid4())
        task_name = self.name or self.__class__.__name__

        job, created = TaskJob.objects.get_or_create(
            task_id=task_id,
            defaults={
                "name": task_name,
                "status": TaskJob.Status.RUNNING,
                "progress": 0,
            },
        )
        if not created and job.status != TaskJob.Status.RUNNING:
            job.mark_started()

        self.job = job

        try:
            result = super().__call__(*args, **kwargs)
            job.mark_success(result=result)
            return result
        except Exception as exc:
            tb = traceback.format_exc()
            logger.error("Error executing background task %s [%s]: %s", task_name, task_id, exc)
            job.mark_failure(error=str(exc), traceback_str=tb)
            raise

    def update_job_progress(self, percent: int, log_line: str = None):
        """Helper for task logic to update completion percentage and append log output."""
        if hasattr(self, "job") and self.job:
            self.job.update_progress(percent, log_line=log_line)
