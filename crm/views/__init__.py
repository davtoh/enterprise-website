"""
CRM Views Package — Modular View Subsystem
Decomposed from monolithic crm/views.py (730 lines) into domain submodules:
- base.py: CRMBaseView, DashboardView, PipelineView, AnalyticsView, AnalyticsDataApiView, EmailTrackingPixelView
- leads.py: Lead CRUD, stage transitions, and interaction appending
- contacts.py: Contact CRUD and physical security clearance filters
- companies.py: Company CRUD
- sequences.py: Email sequences, steps, and Celery dispatch
- segments.py: Dynamic customer segmentation and broadcast campaigns
"""

from .base import (
    CRMBaseView,
    DashboardView,
    PipelineView,
    AnalyticsView,
    AnalyticsDataApiView,
    TRANSPARENT_GIF,
    EmailTrackingPixelView,
)
from .leads import (
    LeadStageUpdateView,
    LeadListView,
    LeadDetailView,
    LeadCreateView,
    LeadUpdateView,
    LeadDeleteView,
    LeadAddInteractionView,
)
from .contacts import (
    ContactListView,
    ContactDetailView,
    ContactCreateView,
    ContactUpdateView,
    ContactDeleteView,
)
from .companies import (
    CompanyListView,
    CompanyDetailView,
    CompanyCreateView,
    CompanyUpdateView,
    CompanyDeleteView,
)
from .sequences import (
    SequenceListView,
    SequenceDetailView,
    SequenceCreateView,
    SequenceUpdateView,
    SequenceDeleteView,
    EmailStepCreateView,
    EmailStepUpdateView,
    EmailStepDeleteView,
    ProcessSequencesNowView,
)
from .segments import (
    SegmentListView,
    SegmentDetailView,
    SegmentCreateView,
    SegmentUpdateView,
    SegmentDeleteView,
    SegmentBroadcastView,
)

__all__ = [
    "CRMBaseView",
    "DashboardView",
    "PipelineView",
    "AnalyticsView",
    "AnalyticsDataApiView",
    "TRANSPARENT_GIF",
    "EmailTrackingPixelView",
    "LeadStageUpdateView",
    "LeadListView",
    "LeadDetailView",
    "LeadCreateView",
    "LeadUpdateView",
    "LeadDeleteView",
    "LeadAddInteractionView",
    "ContactListView",
    "ContactDetailView",
    "ContactCreateView",
    "ContactUpdateView",
    "ContactDeleteView",
    "CompanyListView",
    "CompanyDetailView",
    "CompanyCreateView",
    "CompanyUpdateView",
    "CompanyDeleteView",
    "SequenceListView",
    "SequenceDetailView",
    "SequenceCreateView",
    "SequenceUpdateView",
    "SequenceDeleteView",
    "EmailStepCreateView",
    "EmailStepUpdateView",
    "EmailStepDeleteView",
    "ProcessSequencesNowView",
    "SegmentListView",
    "SegmentDetailView",
    "SegmentCreateView",
    "SegmentUpdateView",
    "SegmentDeleteView",
    "SegmentBroadcastView",
]

