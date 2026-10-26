from django.urls import path
from . import views

app_name = "intelligent_tracker_hub"

urlpatterns = [
    path("", views.SecurityDashboardView.as_view(), name="dashboard"),
    path("events/<uuid:event_id>/", views.SecurityEventDetailView.as_view(), name="event_detail"),
    path("events/<uuid:event_id>/resolve/", views.SecurityEventResolveView.as_view(), name="event_resolve"),
    path("audit/", views.SecurityAuditLogListView.as_view(), name="audit_log"),
    path("simulate/", views.SecurityMockDispatchView.as_view(), name="simulate_dispatch"),
]
