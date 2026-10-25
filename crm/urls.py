from django.urls import path
from . import views

app_name = "crm"

urlpatterns = [
    # Dashboard & Pipeline
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("pipeline/", views.PipelineView.as_view(), name="pipeline"),

    # Leads
    path("leads/", views.LeadListView.as_view(), name="lead_list"),
    path("leads/new/", views.LeadCreateView.as_view(), name="lead_create"),
    path("leads/<int:pk>/", views.LeadDetailView.as_view(), name="lead_detail"),
    path("leads/<int:pk>/edit/", views.LeadUpdateView.as_view(), name="lead_update"),
    path("leads/<int:pk>/delete/", views.LeadDeleteView.as_view(), name="lead_delete"),
    path("leads/<int:pk>/stage/", views.LeadStageUpdateView.as_view(), name="lead_stage_update"),
    path("leads/<int:pk>/interactions/add/", views.LeadAddInteractionView.as_view(), name="lead_add_interaction"),

    # Contacts
    path("contacts/", views.ContactListView.as_view(), name="contact_list"),
    path("contacts/new/", views.ContactCreateView.as_view(), name="contact_create"),
    path("contacts/<int:pk>/", views.ContactDetailView.as_view(), name="contact_detail"),
    path("contacts/<int:pk>/edit/", views.ContactUpdateView.as_view(), name="contact_update"),
    path("contacts/<int:pk>/delete/", views.ContactDeleteView.as_view(), name="contact_delete"),

    # Companies
    path("companies/", views.CompanyListView.as_view(), name="company_list"),
    path("companies/new/", views.CompanyCreateView.as_view(), name="company_create"),
    path("companies/<int:pk>/", views.CompanyDetailView.as_view(), name="company_detail"),
    path("companies/<int:pk>/edit/", views.CompanyUpdateView.as_view(), name="company_update"),
    path("companies/<int:pk>/delete/", views.CompanyDeleteView.as_view(), name="company_delete"),

    # Email Sequences
    path("sequences/", views.SequenceListView.as_view(), name="sequence_list"),
    path("sequences/new/", views.SequenceCreateView.as_view(), name="sequence_create"),
    path("sequences/<int:pk>/", views.SequenceDetailView.as_view(), name="sequence_detail"),
    path("sequences/<int:pk>/edit/", views.SequenceUpdateView.as_view(), name="sequence_update"),
    path("sequences/<int:pk>/delete/", views.SequenceDeleteView.as_view(), name="sequence_delete"),
    path("sequences/<int:pk>/steps/new/", views.EmailStepCreateView.as_view(), name="step_create"),
    path("sequences/<int:pk>/steps/<int:step_pk>/edit/", views.EmailStepUpdateView.as_view(), name="step_update"),
    path("sequences/<int:pk>/steps/<int:step_pk>/delete/", views.EmailStepDeleteView.as_view(), name="step_delete"),
    path("sequences/process-now/", views.ProcessSequencesNowView.as_view(), name="process_sequences_now"),

    # Customer Segments
    path("segments/", views.SegmentListView.as_view(), name="segment_list"),
    path("segments/new/", views.SegmentCreateView.as_view(), name="segment_create"),
    path("segments/<int:pk>/", views.SegmentDetailView.as_view(), name="segment_detail"),
    path("segments/<int:pk>/edit/", views.SegmentUpdateView.as_view(), name="segment_update"),
    path("segments/<int:pk>/delete/", views.SegmentDeleteView.as_view(), name="segment_delete"),
    path("segments/<int:pk>/broadcast/", views.SegmentBroadcastView.as_view(), name="segment_broadcast"),

    # Analytics Dashboard
    path("analytics/", views.AnalyticsView.as_view(), name="analytics"),
    path("analytics/data/", views.AnalyticsDataApiView.as_view(), name="analytics_data"),

    # Email Tracking Pixel
    path("track/<uuid:token>.png", views.EmailTrackingPixelView.as_view(), name="email_tracking_pixel"),
]
