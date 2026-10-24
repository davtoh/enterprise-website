from django.urls import path
from . import views

app_name = "task_runner"

urlpatterns = [
    path("", views.TaskJobListView.as_view(), name="list"),
    path("trigger/", views.TaskTriggerView.as_view(), name="trigger"),
    path("<str:task_id>/status/", views.TaskJobStatusAPIView.as_view(), name="status"),
    path("<str:task_id>/", views.TaskJobDetailView.as_view(), name="detail"),
]
