"""
Test Suite Facade: CRM Subsystem.

Backward-compatible re-export module routing tests to focused domain test modules in `tests/crm/`:
- `test_models`: Model methods, validation, relationships, and customer segmentation filters.
- `test_tasks_and_utils`: Template rendering, email sequence processor, and broadcast dispatch.
- `test_views`: HTTP view endpoints, pipeline Kanban, CRUD operations, and tracking pixel.
"""

from .crm.conftest import (
    auth_user,
    test_company,
    test_contact,
    test_lead,
)

from .crm.test_models import (
    test_company_model,
    test_contact_model,
    test_lead_model_and_stage_transitions,
    test_interaction_log_model,
    test_email_sequence_and_step_models,
    test_auto_enroll_lead_in_sequences,
    test_delivery_log_and_tracking,
    test_customer_segment_filtering,
)

from .crm.test_tasks_and_utils import (
    test_render_email_content,
    test_process_email_sequences_task,
    test_send_segment_broadcast_task,
    test_crm_analytics_data,
)

from .crm.test_views import (
    test_crm_views_unauthenticated_redirect,
    test_dashboard_and_pipeline_views,
    test_lead_stage_update_view,
    test_lead_crud_views,
    test_contact_crud_views,
    test_company_crud_views,
    test_sequence_views,
    test_segment_views_and_broadcast,
    test_analytics_views,
    test_email_tracking_pixel,
    test_crm_plugin_registration,
)
