from django import template
from task_runner.models import TaskJob

register = template.Library()


@register.inclusion_tag("task_runner/task_progress_widget.html", takes_context=True)
def task_progress_widget(context, task_id, title=None, auto_connect=True):
    """
    Renders an interactive real-time background task monitoring widget.
    Subscribes via WebSocket (ws/tasks/<task_id>/) with fallback to HTTP polling.
    """
    job = None
    if task_id:
        job = TaskJob.objects.filter(task_id=str(task_id)).first()

    return {
        "task_id": str(task_id) if task_id else "",
        "job": job,
        "title": title or (job.name if job else "Background Task"),
        "status": job.status if job else "PENDING",
        "progress": job.progress if job else 0,
        "log_output": job.log_output if job else "",
        "error_message": job.error_message if job else "",
        "auto_connect": auto_connect,
    }
