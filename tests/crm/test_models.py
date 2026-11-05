from decimal import Decimal
import pytest
from django.urls import reverse

from crm.models import (
    Company,
    Contact,
    Lead,
    LeadStage,
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

