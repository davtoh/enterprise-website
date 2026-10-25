import datetime
import json
import uuid
from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from crm.models import (
    Company,
    Contact,
    Lead,
    LeadStage,
    LeadSource,
    InteractionLog,
    InteractionType,
    EmailSequence,
    EmailStep,
    SequenceEnrollment,
    SequenceEnrollmentStatus,
    EmailDeliveryLog,
    EmailDeliveryStatus,
    Segment,
)
from crm.forms import (
    CompanyForm,
    ContactForm,
    LeadForm,
    InteractionLogForm,
    EmailSequenceForm,
    EmailStepForm,
    SegmentForm,
    BroadcastEmailForm,
)
from crm.plugin import CRMPlugin
from crm.tasks import process_email_sequences, send_segment_broadcast
from crm.utils import (
    auto_enroll_lead_in_sequences,
    render_email_content,
    get_crm_analytics_data,
)

User = get_user_model()


@pytest.fixture
def auth_user(db):
    return User.objects.create_user(
        username="crm_agent",
        email="crm_agent@example.com",
        password="ValidPassword123!",
        is_staff=True,
    )


@pytest.fixture
def test_company(db):
    return Company.objects.create(
        name="Acme Corp",
        industry="Technology",
        website="https://acme.example.com",
        city="Austin",
        country="US",
        annual_revenue=Decimal("1500000.00"),
    )


@pytest.fixture
def test_contact(db, test_company):
    return Contact.objects.create(
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        phone="+1555123456",
        company=test_company,
        job_title="VP of Sales",
        tags="enterprise, vip",
        is_subscribed=True,
    )


@pytest.fixture
def test_lead(db, test_contact, test_company, auth_user):
    return Lead.objects.create(
        title="Acme Cloud Platform Expansion",
        contact=test_contact,
        company=test_company,
        stage=LeadStage.NEW,
        source=LeadSource.WEBSITE,
        value=Decimal("45000.00"),
        assigned_to=auth_user,
    )


# ==============================================================================
# Model Tests
# ==============================================================================

@pytest.mark.django_db
def test_company_model(test_company, test_lead):
    assert str(test_company) == "Acme Corp"
    assert test_company.get_absolute_url() == reverse("crm:company_detail", kwargs={"pk": test_company.pk})
    assert test_company.total_pipeline_value == Decimal("45000.00")


@pytest.mark.django_db
def test_contact_model(test_contact):
    assert test_contact.full_name == "Jane Doe"
    assert str(test_contact) == "Jane Doe"
    assert test_contact.tag_list == ["enterprise", "vip"]
    assert test_contact.get_absolute_url() == reverse("crm:contact_detail", kwargs={"pk": test_contact.pk})


@pytest.mark.django_db
def test_lead_model_and_stage_transitions(test_lead, auth_user):
    assert "Acme Cloud Platform Expansion" in str(test_lead)
    assert test_lead.get_absolute_url() == reverse("crm:lead_detail", kwargs={"pk": test_lead.pk})

    # Test stage change
    changed = test_lead.change_stage(LeadStage.QUALIFIED, user=auth_user, note="Customer confirmed budget.")
    assert changed is True
    test_lead.refresh_from_db()
    assert test_lead.stage == LeadStage.QUALIFIED

    # Check automatic InteractionLog generation
    log = InteractionLog.objects.filter(lead=test_lead, interaction_type=InteractionType.STAGE_CHANGE).first()
    assert log is not None
    assert "Stage changed" in log.summary
    assert "Customer confirmed budget." in log.details
    assert log.user == auth_user

    # No-op change with same stage
    same_changed = test_lead.change_stage(LeadStage.QUALIFIED)
    assert same_changed is False

    # Invalid stage raises ValueError
    with pytest.raises(ValueError):
        test_lead.change_stage("invalid_stage_code")


@pytest.mark.django_db
def test_interaction_log_model(test_lead, test_contact, auth_user):
    log = InteractionLog.objects.create(
        lead=test_lead,
        contact=test_contact,
        user=auth_user,
        interaction_type=InteractionType.CALL,
        summary="Discovery Phone Call",
        details="Discussed requirements and deployment timeline.",
    )
    assert "[Phone Call] Discovery Phone Call" in str(log)


@pytest.mark.django_db
def test_email_sequence_and_step_models(db):
    seq = EmailSequence.objects.create(
        name="Enterprise Onboarding Drip",
        trigger_stage=LeadStage.QUALIFIED,
        is_active=True,
    )
    step1 = EmailStep.objects.create(
        sequence=seq,
        step_number=1,
        delay_days=0,
        subject="Welcome {{ contact.first_name }} to Enterprise Website!",
        body_template="Hi {{ contact.first_name }},\nThanks for reaching out from {{ company.name }}.",
    )
    step2 = EmailStep.objects.create(
        sequence=seq,
        step_number=2,
        delay_days=3,
        subject="Follow-up on {{ lead.title }}",
        body_template="Checking in on our proposal.",
    )

    assert str(seq) == "Enterprise Onboarding Drip"
    assert seq.total_steps == 2
    assert "Step 1" in str(step1)


@pytest.mark.django_db
def test_auto_enroll_lead_in_sequences(test_contact, test_company, auth_user):
    seq = EmailSequence.objects.create(
        name="Qualified Lead Drip",
        trigger_stage=LeadStage.QUALIFIED,
        is_active=True,
    )
    lead = Lead.objects.create(
        title="SaaS Upgrade",
        contact=test_contact,
        company=test_company,
        stage=LeadStage.NEW,
        value=Decimal("10000.00"),
    )

    # Change stage to Qualified
    lead.change_stage(LeadStage.QUALIFIED, user=auth_user)

    # Verify contact was auto-enrolled
    enrollment = SequenceEnrollment.objects.filter(sequence=seq, contact=test_contact, lead=lead).first()
    assert enrollment is not None
    assert enrollment.status == SequenceEnrollmentStatus.ACTIVE
    assert enrollment.current_step_number == 1


@pytest.mark.django_db
def test_delivery_log_and_tracking(db, test_contact):
    delivery = EmailDeliveryLog.objects.create(
        contact=test_contact,
        recipient_email=test_contact.email,
        subject="Intro email",
        status=EmailDeliveryStatus.SENT,
    )
    assert delivery.status == EmailDeliveryStatus.SENT
    assert delivery.opened_at is None

    delivery.record_opened()
    delivery.refresh_from_db()
    assert delivery.status == EmailDeliveryStatus.OPENED
    assert delivery.opened_at is not None


@pytest.mark.django_db
def test_customer_segment_filtering(db, test_company, test_contact, test_lead):
    # Contact 2 in UK
    company_uk = Company.objects.create(name="London Systems", country="UK")
    contact_uk = Contact.objects.create(
        first_name="Arthur",
        last_name="Pendleton",
        email="arthur@example.co.uk",
        company=company_uk,
        tags="smb",
        is_subscribed=False,
    )

    # Segment 1: Country US
    seg_us = Segment.objects.create(
        name="US Accounts",
        filter_rules={"country": "US"},
    )
    matching_us = seg_us.get_matching_contacts()
    assert test_contact in matching_us
    assert contact_uk not in matching_us
    assert seg_us.contact_count == 1

    # Segment 2: Subscribed contacts
    seg_sub = Segment.objects.create(
        name="Subscribed Leads",
        filter_rules={"subscribed": True},
    )
    assert test_contact in seg_sub.get_matching_contacts()
    assert contact_uk not in seg_sub.get_matching_contacts()

    # Segment 3: Min value
    seg_high_val = Segment.objects.create(
        name="High Value Deals",
        filter_rules={"min_value": 20000},
    )
    matching_leads = seg_high_val.get_matching_leads()
    assert test_lead in matching_leads


# ==============================================================================
# Helper & Task Tests
# ==============================================================================

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


@pytest.mark.django_db
def test_process_email_sequences_task(db, test_contact, test_lead):
    seq = EmailSequence.objects.create(name="Onboarding Drip", is_active=True)
    step1 = EmailStep.objects.create(
        sequence=seq,
        step_number=1,
        delay_days=0,
        subject="Step 1 Subject",
        body_template="Hello step 1",
    )
    step2 = EmailStep.objects.create(
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


# ==============================================================================
# View & HTTP Endpoint Tests
# ==============================================================================

@pytest.mark.django_db
def test_crm_views_unauthenticated_redirect(client):
    urls = [
        reverse("crm:dashboard"),
        reverse("crm:pipeline"),
        reverse("crm:lead_list"),
        reverse("crm:contact_list"),
        reverse("crm:company_list"),
        reverse("crm:sequence_list"),
        reverse("crm:segment_list"),
        reverse("crm:analytics"),
    ]
    for u in urls:
        resp = client.get(u)
        assert "/accounts/login" in resp.url


@pytest.mark.django_db
def test_dashboard_and_pipeline_views(client, auth_user, test_lead):
    client.force_login(auth_user)

    resp = client.get(reverse("crm:dashboard"))
    assert resp.status_code == 200
    assert "Acme Cloud Platform Expansion" in resp.content.decode()

    resp_pipe = client.get(reverse("crm:pipeline"))
    assert resp_pipe.status_code == 200
    assert "Kanban" in resp_pipe.content.decode()


@pytest.mark.django_db
def test_lead_stage_update_view(client, auth_user, test_lead):
    client.force_login(auth_user)

    url = reverse("crm:lead_stage_update", kwargs={"pk": test_lead.pk})
    resp = client.post(url, {"stage": LeadStage.WON, "note": "Deal signed!"})
    assert resp.status_code == 302

    test_lead.refresh_from_db()
    assert test_lead.stage == LeadStage.WON

    # Test invalid stage returns 400
    bad_resp = client.post(url, {"stage": "non_existent"})
    assert bad_resp.status_code == 400


@pytest.mark.django_db
def test_lead_crud_views(client, auth_user, test_contact, test_company):
    client.force_login(auth_user)

    # Create Lead
    create_url = reverse("crm:lead_create")
    post_data = {
        "title": "New Enterprise License",
        "contact": test_contact.pk,
        "company": test_company.pk,
        "stage": LeadStage.NEW,
        "source": LeadSource.WEBSITE,
        "value": "25000.00",
        "notes": "Interested in 50 seats",
    }
    resp = client.post(create_url, post_data)
    assert resp.status_code == 302
    created_lead = Lead.objects.get(title="New Enterprise License")
    assert created_lead.value == Decimal("25000.00")

    # Detail View
    detail_url = reverse("crm:lead_detail", kwargs={"pk": created_lead.pk})
    resp_detail = client.get(detail_url)
    assert resp_detail.status_code == 200
    assert "New Enterprise License" in resp_detail.content.decode()

    # Add Interaction to Lead
    add_act_url = reverse("crm:lead_add_interaction", kwargs={"pk": created_lead.pk})
    client.post(add_act_url, {
        "interaction_type": InteractionType.NOTE,
        "summary": "Demo scheduled for next Tuesday.",
        "details": "Zoom link shared.",
    })
    assert created_lead.interactions.filter(summary="Demo scheduled for next Tuesday.").exists()

    # Update Lead
    update_url = reverse("crm:lead_update", kwargs={"pk": created_lead.pk})
    client.post(update_url, {
        **post_data,
        "title": "New Enterprise License (50 Seats)",
    })
    created_lead.refresh_from_db()
    assert created_lead.title == "New Enterprise License (50 Seats)"

    # Delete Lead
    delete_url = reverse("crm:lead_delete", kwargs={"pk": created_lead.pk})
    resp_del = client.post(delete_url)
    assert resp_del.status_code == 302
    assert not Lead.objects.filter(pk=created_lead.pk).exists()


@pytest.mark.django_db
def test_contact_crud_views(client, auth_user, test_company):
    client.force_login(auth_user)

    # Create contact
    resp = client.post(reverse("crm:contact_create"), {
        "first_name": "Alice",
        "last_name": "Smith",
        "email": "alice.smith@example.com",
        "company": test_company.pk,
        "job_title": "CTO",
        "is_subscribed": True,
        "tags": "tech, decision-maker",
    })
    assert resp.status_code == 302
    contact = Contact.objects.get(email="alice.smith@example.com")
    assert contact.full_name == "Alice Smith"

    # Detail view
    resp_detail = client.get(reverse("crm:contact_detail", kwargs={"pk": contact.pk}))
    assert resp_detail.status_code == 200
    assert "Alice Smith" in resp_detail.content.decode()

    # Delete contact
    client.post(reverse("crm:contact_delete", kwargs={"pk": contact.pk}))
    assert not Contact.objects.filter(pk=contact.pk).exists()


@pytest.mark.django_db
def test_company_crud_views(client, auth_user):
    client.force_login(auth_user)

    resp = client.post(reverse("crm:company_create"), {
        "name": "Global Corp",
        "industry": "Finance",
        "city": "New York",
        "country": "US",
        "annual_revenue": "5000000.00",
    })
    assert resp.status_code == 302
    company = Company.objects.get(name="Global Corp")

    resp_detail = client.get(reverse("crm:company_detail", kwargs={"pk": company.pk}))
    assert resp_detail.status_code == 200
    assert "Global Corp" in resp_detail.content.decode()

    client.post(reverse("crm:company_delete", kwargs={"pk": company.pk}))
    assert not Company.objects.filter(pk=company.pk).exists()


@pytest.mark.django_db
def test_sequence_views(client, auth_user):
    client.force_login(auth_user)

    # Create Sequence
    resp = client.post(reverse("crm:sequence_create"), {
        "name": "Trial Nurture",
        "trigger_stage": LeadStage.NEW,
        "is_active": True,
        "description": "Nurture new trial leads",
    })
    assert resp.status_code == 302
    seq = EmailSequence.objects.get(name="Trial Nurture")

    # Add Step
    resp_step = client.post(reverse("crm:step_create", kwargs={"pk": seq.pk}), {
        "step_number": 1,
        "delay_days": 1,
        "subject": "Getting started with your trial",
        "body_template": "Hi {{ contact.first_name }}, here is your starter guide.",
    })
    assert resp_step.status_code == 302
    assert seq.steps.count() == 1

    # Detail View
    resp_detail = client.get(reverse("crm:sequence_detail", kwargs={"pk": seq.pk}))
    assert resp_detail.status_code == 200
    assert "Getting started with your trial" in resp_detail.content.decode()

    # Trigger process now
    resp_proc = client.post(reverse("crm:process_sequences_now"))
    assert resp_proc.status_code == 302


@pytest.mark.django_db
def test_segment_views_and_broadcast(client, auth_user, test_contact):
    client.force_login(auth_user)

    # Create Segment
    resp = client.post(reverse("crm:segment_create"), {
        "name": "VIP Subscribed",
        "description": "High tier subscribers",
        "filter_rules": json.dumps({"subscribed": True}),
    })
    assert resp.status_code == 302
    seg = Segment.objects.get(name="VIP Subscribed")

    # Detail View
    resp_detail = client.get(reverse("crm:segment_detail", kwargs={"pk": seg.pk}))
    assert resp_detail.status_code == 200
    assert "VIP Subscribed" in resp_detail.content.decode()

    # Broadcast View
    mail.outbox.clear()
    resp_broad = client.post(reverse("crm:segment_broadcast", kwargs={"pk": seg.pk}), {
        "subject": "Exclusive Webinar Invitation",
        "message": "Join us tomorrow for an exclusive product deep-dive.",
    })
    assert resp_broad.status_code == 302
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == "Exclusive Webinar Invitation"


@pytest.mark.django_db
def test_analytics_views(client, auth_user, test_lead):
    client.force_login(auth_user)

    # HTML page
    resp = client.get(reverse("crm:analytics"))
    assert resp.status_code == 200
    assert "Funnel Win Rate" in resp.content.decode()

    # JSON Data endpoint
    resp_data = client.get(reverse("crm:analytics_data"))
    assert resp_data.status_code == 200
    data = resp_data.json()
    assert "kpi" in data
    assert "funnel" in data
    assert "pipeline_revenue" in data


@pytest.mark.django_db
def test_email_tracking_pixel(client, test_contact):
    delivery = EmailDeliveryLog.objects.create(
        contact=test_contact,
        recipient_email=test_contact.email,
        subject="Tracking Test",
        status=EmailDeliveryStatus.SENT,
    )
    url = reverse("crm:email_tracking_pixel", kwargs={"token": delivery.tracking_token})
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp["Content-Type"] == "image/gif"

    delivery.refresh_from_db()
    assert delivery.status == EmailDeliveryStatus.OPENED
    assert delivery.opened_at is not None


def test_crm_plugin_registration():
    assert CRMPlugin.name == "crm"
    assert CRMPlugin.category == "productivity"
    assert len(CRMPlugin.get_menu_items()) == 1
    assert CRMPlugin.get_menu_items()[0].url_name == "crm:dashboard"
    assert "crm.process_email_sequences" in CRMPlugin.get_tasks()
