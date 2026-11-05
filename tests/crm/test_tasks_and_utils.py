import datetime
import uuid
import pytest
from django.core import mail
from django.utils import timezone

from crm.models import (
    EmailSequence,
    EmailStep,
    SequenceEnrollment,
    SequenceEnrollmentStatus,
    EmailDeliveryLog,
    EmailDeliveryStatus,
    Segment,
)
from crm.tasks import process_email_sequences, send_segment_broadcast
from crm.utils import (
    render_email_content,
    get_crm_analytics_data,
)


@pytest.mark.django_db
def test_render_email_content(test_contact, test_lead):
    step = EmailStep(
        step_number=1,
        subject="Hello {{ contact.first_name }}!",
        body_template="Deal {{ lead.title }} with {{ company.name }}.\n{{ tracking_pixel }}",
    )
    subj, body = render_email_content(
        step=step,
        contact=test_contact,
        lead=test_lead,
        tracking_token=uuid.uuid4(),
        base_url="http://localhost:8000",
    )
    assert subj == "Hello Jane!"
    assert "Acme Cloud Platform Expansion" in body
    assert "Acme Corp" in body
    assert "crm/track/" in body


def _setup_active_sequence_and_step(test_contact, test_lead):
    seq = EmailSequence.objects.create(name="Onboarding Drip", is_active=True)
    EmailStep.objects.create(
        sequence=seq,
        step_number=1,
        delay_days=0,
        subject="Step 1 Subject",
        body_template="Hello step 1",
    )
    EmailStep.objects.create(
        sequence=seq,
        step_number=2,
        delay_days=2,
        subject="Step 2 Subject",
        body_template="Hello step 2",
    )
    enrollment = SequenceEnrollment.objects.create(
        sequence=seq,
        contact=test_contact,
        lead=test_lead,
        current_step_number=1,
        status=SequenceEnrollmentStatus.ACTIVE,
        next_send_at=timezone.now() - datetime.timedelta(minutes=5),
    )
    return enrollment


@pytest.mark.django_db
def test_process_email_sequences_task(db, test_contact, test_lead):
    enrollment = _setup_active_sequence_and_step(test_contact, test_lead)

    mail.outbox.clear()
    result = process_email_sequences()
    assert result["processed"] == 1
    assert result["sent"] == 1
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [test_contact.email]
    assert mail.outbox[0].subject == "Step 1 Subject"

    # Enrollment should advance to step 2
    enrollment.refresh_from_db()
    assert enrollment.current_step_number == 2
    assert enrollment.status == SequenceEnrollmentStatus.ACTIVE

    # Deliver log created
    delivery = EmailDeliveryLog.objects.filter(enrollment=enrollment).first()
    assert delivery is not None
    assert delivery.status == EmailDeliveryStatus.SENT


@pytest.mark.django_db
def test_send_segment_broadcast_task(db, test_contact, auth_user):
    seg = Segment.objects.create(
        name="All Subscribed",
        filter_rules={"subscribed": True},
    )
    mail.outbox.clear()
    res = send_segment_broadcast(
        segment_id=seg.pk,
        subject="Spring Sale Announcement",
        message="<p>Special offer for our partners.</p>",
        sender_user_id=auth_user.pk,
    )
    assert res["sent_count"] == 1
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [test_contact.email]
    assert mail.outbox[0].subject == "Spring Sale Announcement"


@pytest.mark.django_db
def test_crm_analytics_data(test_lead, test_contact):
    data = get_crm_analytics_data()
    assert "kpi" in data
    assert "funnel" in data
    assert "pipeline_revenue" in data
    assert "monthly_contacts" in data
    assert "email_stats" in data
    assert data["kpi"]["total_leads"] == 1
    assert data["kpi"]["total_contacts"] == 1
