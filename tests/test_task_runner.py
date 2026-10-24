import json
import pytest
from unittest.mock import patch
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.urls import reverse
from channels.testing import WebsocketCommunicator
from enterprise_website.routing import application

from task_runner.models import TaskJob
from task_runner.tasks import run_auto_translate, run_collectstatic, run_external_script
from task_runner.base import TrackedTask
from celery import shared_task
from plugin_registry import registry

User = get_user_model()


@pytest.fixture
def staff_user(db):
    user = User.objects.create_user(
        username="admin_tester",
        email="admin@example.com",
        password="TestPassword123!",
        is_staff=True,
    )
    return user


@pytest.fixture
def regular_user(db):
    user = User.objects.create_user(
        username="regular_tester",
        email="user@example.com",
        password="TestPassword123!",
        is_staff=False,
    )
    return user


@pytest.fixture
def sample_job(db, staff_user):
    return TaskJob.objects.create(
        task_id="test-task-uuid-1234",
        name="Sample Background Task",
        status=TaskJob.Status.PENDING,
        progress=0,
        log_output="Task registered.",
        created_by=staff_user,
    )


@pytest.mark.django_db
class TestTaskJobModel:
    """Tests for the TaskJob model lifecycle, state transitions, and logging."""

    def test_task_job_defaults(self, sample_job):
        assert sample_job.status == TaskJob.Status.PENDING
        assert sample_job.progress == 0
        assert "Sample Background Task" in str(sample_job)
        assert sample_job.to_dict()["task_id"] == "test-task-uuid-1234"
        assert sample_job.to_dict()["created_by"] == "admin_tester"

    def test_update_progress(self, sample_job):
        sample_job.update_progress(45, log_line="Processed batch 1")
        sample_job.refresh_from_db()
        assert sample_job.progress == 45
        assert "Processed batch 1" in sample_job.log_output

        # Clamp boundaries
        sample_job.update_progress(150)
        assert sample_job.progress == 100
        sample_job.update_progress(-20)
        assert sample_job.progress == 0

    def test_mark_started_and_success(self, sample_job):
        sample_job.mark_started(log_line="Worker started processing")
        sample_job.refresh_from_db()
        assert sample_job.status == TaskJob.Status.RUNNING
        assert "Worker started processing" in sample_job.log_output

        sample_job.mark_success(result={"files": 42}, log_line="Done!")
        sample_job.refresh_from_db()
        assert sample_job.status == TaskJob.Status.SUCCESS
        assert sample_job.progress == 100
        assert '{"files": 42}' in sample_job.result_data
        assert "Done!" in sample_job.log_output

    def test_mark_failure(self, sample_job):
        sample_job.mark_failure(error="Connection timed out", traceback_str="Traceback details...")
        sample_job.refresh_from_db()
        assert sample_job.status == TaskJob.Status.FAILURE
        assert sample_job.error_message == "Connection timed out"
        assert "[ERROR] Traceback details..." in sample_job.log_output


@pytest.mark.django_db
class TestTrackedTaskAndCelery:
    """Tests for TrackedTask Celery base class and example background tasks."""

    def test_tracked_task_success(self):
        @shared_task(base=TrackedTask, bind=True, name="test.dummy_success")
        def dummy_task(self):
            self.update_job_progress(50, "Working...")
            return "SUCCESS_RESULT"

        # Run synchronously in eager mode
        res = dummy_task.apply()
        assert res.get() == "SUCCESS_RESULT"

        job = TaskJob.objects.filter(name="test.dummy_success").first()
        assert job is not None
        assert job.status == TaskJob.Status.SUCCESS
        assert job.progress == 100
        assert "Working..." in job.log_output

    def test_tracked_task_failure(self):
        @shared_task(base=TrackedTask, bind=True, name="test.dummy_failure")
        def failing_task(self):
            raise ValueError("Intentional crash for testing")

        with pytest.raises(ValueError, match="Intentional crash for testing"):
            failing_task.apply()

        job = TaskJob.objects.filter(name="test.dummy_failure").first()
        assert job is not None
        assert job.status == TaskJob.Status.FAILURE
        assert "Intentional crash for testing" in job.error_message

    @patch("task_runner.tasks.call_command")
    def test_run_collectstatic_task(self, mock_call):
        res = run_collectstatic.apply(kwargs={"clear": False})
        assert res.get() == {"status": "success"}
        mock_call.assert_called_once()
        job = TaskJob.objects.filter(name="task_runner.run_collectstatic").first()
        assert job.status == TaskJob.Status.SUCCESS

    @patch("task_runner.tasks.call_command")
    def test_run_auto_translate_task(self, mock_call):
        res = run_auto_translate.apply(kwargs={"lang": "es", "backend": "mymemory", "max_entries": 3})
        assert res.get()["status"] == "success"
        mock_call.assert_called_once()
        job = TaskJob.objects.filter(name="task_runner.run_auto_translate").first()
        assert job.status == TaskJob.Status.SUCCESS

    def test_run_external_script_task_success(self):
        # Run a quick python echo command
        res = run_external_script.apply(args=['python -c "print(\'Hello Celery\')"'])
        assert res.get()["status"] == "success"
        assert res.get()["exit_code"] == 0

        job = TaskJob.objects.filter(name="task_runner.run_external_script").first()
        assert job is not None
        assert job.status == TaskJob.Status.SUCCESS
        assert "Hello Celery" in job.log_output

    def test_run_external_script_task_failure(self):
        with pytest.raises(RuntimeError):
            run_external_script.apply(args=['python -c "import sys; sys.exit(42)"'])

        job = TaskJob.objects.filter(name="task_runner.run_external_script").latest("created_at")
        assert job.status == TaskJob.Status.FAILURE
        assert "42" in job.error_message or "42" in job.log_output


@pytest.mark.django_db(transaction=True)
class TestTaskProgressConsumer:
    """Tests for Django Channels TaskProgressConsumer WebSocket communication."""

    def test_websocket_connect_and_receive_snapshot(self):
        import asyncio

        job = TaskJob.objects.create(
            task_id="ws-task-uuid-999",
            name="WebSocket Streaming Job",
            status=TaskJob.Status.RUNNING,
            progress=40,
            log_output="Initial line\n",
        )

        async def _test():
            communicator = WebsocketCommunicator(application, "ws/tasks/ws-task-uuid-999/")
            connected, _ = await communicator.connect()
            assert connected is True

            # First message should be the initial snapshot
            response = await communicator.receive_json_from(timeout=3)
            assert response["task_id"] == "ws-task-uuid-999"
            assert response["status"] == "RUNNING"
            assert response["progress"] == 40
            assert "Initial line" in response["log_output"]

            # Test live broadcast update
            from asgiref.sync import sync_to_async
            await sync_to_async(job.update_progress)(65, log_line="New streaming log")
            broadcast_msg = await communicator.receive_json_from(timeout=3)
            assert broadcast_msg["progress"] == 65
            assert "New streaming log" in broadcast_msg["log_output"]

            await communicator.disconnect()

        asyncio.run(_test())


@pytest.mark.django_db
class TestTaskRunnerViewsAndTemplateTags:
    """Tests for staff views, JSON status API, task launching, and template widget."""

    def test_task_list_permissions(self, client, regular_user, staff_user, sample_job):
        url = reverse("task_runner:list")

        # Anonymous redirected to login
        res = client.get(url)
        assert res.status_code == 302
        assert "/accounts/login" in res.url

        # Regular non-staff redirected / 403
        client.force_login(regular_user)
        res = client.get(url)
        assert res.status_code == 403

        # Staff user gets 200
        client.force_login(staff_user)
        res = client.get(url)
        assert res.status_code == 200
        assert "Background Task Runner" in res.content.decode()
        assert sample_job.name in res.content.decode()

    def test_task_list_filtering_and_search(self, client, staff_user, sample_job):
        client.force_login(staff_user)
        url = reverse("task_runner:list")

        # Search matching
        res = client.get(f"{url}?q=Sample")
        assert sample_job.name in res.content.decode()

        # Search non-matching
        res = client.get(f"{url}?q=NonexistentQueryXYZ")
        assert sample_job.name not in res.content.decode()

        # Status filter matching
        res = client.get(f"{url}?status=PENDING")
        assert sample_job.name in res.content.decode()

        # Status filter non-matching
        res = client.get(f"{url}?status=SUCCESS")
        assert sample_job.name not in res.content.decode()

    def test_task_detail_view(self, client, staff_user, sample_job):
        client.force_login(staff_user)
        url = reverse("task_runner:detail", kwargs={"task_id": sample_job.task_id})
        res = client.get(url)
        assert res.status_code == 200
        assert sample_job.name in res.content.decode()
        assert sample_job.task_id in res.content.decode()

        # Nonexistent task 404
        bad_url = reverse("task_runner:detail", kwargs={"task_id": "nonexistent-id"})
        assert client.get(bad_url).status_code == 404

    def test_task_status_json_api(self, client, sample_job):
        url = reverse("task_runner:status", kwargs={"task_id": sample_job.task_id})
        res = client.get(url)
        assert res.status_code == 200
        data = res.json()
        assert data["task_id"] == sample_job.task_id
        assert data["status"] == "PENDING"
        assert data["progress"] == 0

        # Nonexistent task returns 404
        bad_url = reverse("task_runner:status", kwargs={"task_id": "bad-id"})
        bad_res = client.get(bad_url)
        assert bad_res.status_code == 404

    @patch("task_runner.views.run_auto_translate.apply_async")
    @patch("task_runner.views.run_collectstatic.apply_async")
    @patch("task_runner.views.run_external_script.apply_async")
    def test_task_trigger_view(self, mock_script, mock_collect, mock_translate, client, staff_user):
        client.force_login(staff_user)
        url = reverse("task_runner:trigger")

        # 1. Trigger auto_translate
        res = client.post(url, {"task_type": "auto_translate", "lang": "es", "backend": "mymemory"})
        assert res.status_code == 302
        mock_translate.assert_called_once()

        # 2. Trigger collectstatic
        res = client.post(url, {"task_type": "collectstatic"})
        assert res.status_code == 302
        mock_collect.assert_called_once()

        # 3. Trigger external script
        res = client.post(url, {"task_type": "external_script", "command": "python --version"})
        assert res.status_code == 302
        mock_script.assert_called_once()

        # 4. Unknown task type
        res = client.post(url, {"task_type": "unknown_xyz"})
        assert res.status_code == 302
        assert res.url == reverse("task_runner:list")

    def test_task_progress_widget_template_tag(self, sample_job):
        t = Template("{% load task_runner_tags %}{% task_progress_widget task_id %}")
        c = Context({"task_id": sample_job.task_id})
        rendered = t.render(c)

        assert f"id=\"task-widget-{sample_job.task_id}\"" in rendered
        assert f"id=\"bar-{sample_job.task_id}\"" in rendered
        assert f"id=\"console-{sample_job.task_id}\"" in rendered
        assert "ws/tasks/" in rendered

    def test_plugin_registry_celery_task_integration(self):
        plugin = registry.get_plugin("task_runner")
        assert plugin is not None
        assert "task_runner.run_auto_translate" in plugin.get_tasks()
        assert "task_runner.run_collectstatic" in plugin.get_tasks()
        assert "task_runner.run_external_script" in plugin.get_tasks()

        all_tasks = registry.get_all_tasks()
        assert "task_runner" in all_tasks
        assert "task_runner.run_auto_translate" in all_tasks["task_runner"]

    @patch("task_runner.admin.run_external_script.apply_async")
    def test_admin_launch_script_view(self, mock_apply, client, staff_user, sample_job):
        staff_user.is_superuser = True
        staff_user.save()
        client.force_login(staff_user)
        url = reverse("admin:task_runner_launch_script")

        # GET request renders the form
        get_res = client.get(url)
        assert get_res.status_code == 200
        assert b"Queue External Script in Background" in get_res.content

        # POST request queues task and redirects to change view
        post_res = client.post(url, {"command": "python manage.py check"})
        assert post_res.status_code == 302
        assert "/admin/task_runner/taskjob/" in post_res.url
        mock_apply.assert_called_once()

        # Action redirect test
        changelist_url = reverse("admin:task_runner_taskjob_changelist")
        action_res = client.post(changelist_url, {
            "action": "action_run_external_script",
            admin.helpers.ACTION_CHECKBOX_NAME: [sample_job.pk],
        })
        assert action_res.status_code == 302
        assert action_res.url == url


