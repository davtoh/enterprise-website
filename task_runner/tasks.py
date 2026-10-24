import io
import logging
import os
import shlex
import subprocess
import sys
from pathlib import Path
from celery import shared_task
from django.conf import settings
from django.core.management import call_command
from .base import TrackedTask

logger = logging.getLogger(__name__)


class TaskLogStream(io.StringIO):
    """Custom stream that redirects command stdout/stderr to a TrackedTask live log."""

    def __init__(self, task_instance, initial_progress=10, max_progress=95):
        super().__init__()
        self.task_instance = task_instance
        self.current_progress = initial_progress
        self.max_progress = max_progress

    def write(self, s):
        ret = super().write(s)
        stripped = s.strip()
        if stripped:
            # Advance progress incrementally as output arrives
            if self.current_progress < self.max_progress:
                self.current_progress += 2
            self.task_instance.update_job_progress(
                percent=min(self.max_progress, self.current_progress),
                log_line=stripped,
            )
        return ret


@shared_task(base=TrackedTask, bind=True, name="task_runner.run_auto_translate")
def run_auto_translate(
    self,
    lang=None,
    backend="mymemory",
    no_fuzzy=False,
    skip_mismatched_fuzzy=False,
    no_compile=False,
    max_entries=None,
    delay=0.15,
):
    """
    Executes the auto_translate catalog localization command in the background,
    streaming progress and translation logs live via WebSocket.
    """
    self.update_job_progress(5, f"Starting auto-translate with backend '{backend}'...")
    stream = TaskLogStream(self, initial_progress=10, max_progress=95)

    options = {
        "backend": backend,
        "no_fuzzy": no_fuzzy,
        "skip_mismatched_fuzzy": skip_mismatched_fuzzy,
        "no_compile": no_compile,
        "delay": delay,
        "stdout": stream,
        "stderr": stream,
    }
    if lang:
        options["lang"] = lang
    if max_entries:
        options["max"] = int(max_entries)

    try:
        call_command("auto_translate", **options)
        self.update_job_progress(100, "Auto-translate completed successfully.")
        return {"status": "success", "backend": backend, "lang": lang}
    except Exception as exc:
        self.update_job_progress(100, f"Auto-translate failed: {exc}")
        raise


@shared_task(base=TrackedTask, bind=True, name="task_runner.run_collectstatic")
def run_collectstatic(self, clear=False):
    """
    Collects static files into STATIC_ROOT in the background, streaming output lines.
    """
    self.update_job_progress(5, "Starting background static file collection...")
    stream = TaskLogStream(self, initial_progress=10, max_progress=95)

    options = {
        "interactive": False,
        "stdout": stream,
        "stderr": stream,
    }
    if clear:
        options["clear"] = True

    try:
        call_command("collectstatic", **options)
        self.update_job_progress(100, "Static files collected successfully.")
        return {"status": "success"}
    except Exception as exc:
        self.update_job_progress(100, f"Collectstatic failed: {exc}")
        raise


@shared_task(base=TrackedTask, bind=True, name="task_runner.run_external_script")
def run_external_script(self, command, stdin_data=None, timeout=300):
    """
    Executes an external system script or process, streaming stdout and stderr
    line-by-line in real-time to the TaskJob log and WebSocket.
    """
    self.update_job_progress(5, f"Executing script: {command}")

    # Determine command arguments safely
    if isinstance(command, str):
        if sys.platform == "win32":
            args = command
        else:
            args = shlex.split(command)
    else:
        args = list(command)

    # Prepend active Python virtual environment Scripts directory to PATH
    env = os.environ.copy()
    venv_bin = Path(sys.executable).parent
    env["PATH"] = str(venv_bin) + os.pathsep + env.get("PATH", "")
    env["VIRTUAL_ENV"] = str(venv_bin.parent)
    env["PYTHONUNBUFFERED"] = "1"
    cwd = str(settings.BASE_DIR)

    process = subprocess.Popen(
        args,
        stdin=subprocess.PIPE if stdin_data else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        shell=isinstance(args, str),
        env=env,
        cwd=cwd,
    )

    if stdin_data and process.stdin:
        try:
            process.stdin.write(stdin_data)
            process.stdin.close()
        except Exception as e:
            logger.warning("Error writing stdin to process: %s", e)

    output_lines = []
    line_count = 0

    if process.stdout:
        for raw_line in process.stdout:
            line = raw_line.rstrip()
            output_lines.append(line)
            line_count += 1
            # Advance progress asymptotically toward 90%
            progress = min(90, 10 + (line_count * 5))
            self.update_job_progress(progress, line)

    exit_code = process.wait(timeout=timeout)
    if exit_code != 0:
        err_msg = f"Process exited with non-zero status code: {exit_code}"
        self.update_job_progress(100, err_msg)
        raise RuntimeError(err_msg)

    self.update_job_progress(100, "Script completed successfully.")
    return {
        "status": "success",
        "exit_code": exit_code,
        "lines_emitted": line_count,
    }
