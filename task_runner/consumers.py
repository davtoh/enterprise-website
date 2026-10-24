import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import TaskJob

logger = logging.getLogger(__name__)


class TaskProgressConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer that streams live task progress, status transitions,
    and log lines for a specific background job to connected clients.
    """

    async def connect(self):
        self.task_id = self.scope["url_route"]["kwargs"].get("task_id", "")
        self.group_name = f"task_{self.task_id}"

        await self.accept()

        if self.task_id and self.channel_layer:
            await self.channel_layer.group_add(self.group_name, self.channel_name)

            # Send immediate state snapshot upon connection
            snapshot = await self.get_job_snapshot(self.task_id)
            if snapshot:
                await self.send_json(snapshot)
            else:
                await self.send_json({
                    "task_id": self.task_id,
                    "name": "Background Task",
                    "status": "PENDING",
                    "progress": 0,
                    "log_output": "Connecting to task stream...\n",
                    "error_message": "",
                })

    async def disconnect(self, close_code):
        if hasattr(self, "group_name") and self.channel_layer:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        """Handle client requests (e.g. requesting manual refresh)."""
        if content.get("action") == "refresh":
            snapshot = await self.get_job_snapshot(self.task_id)
            if snapshot:
                await self.send_json(snapshot)

    async def task_update(self, event):
        """Receive broadcast from channel layer group and send to WebSocket client."""
        await self.send_json(event.get("data", {}))

    @database_sync_to_async
    def get_job_snapshot(self, task_id):
        try:
            job = TaskJob.objects.filter(task_id=task_id).first()
            if job:
                return job.to_dict()
        except Exception as e:
            logger.debug("Error fetching job snapshot for %s: %s", task_id, e)
        return None
