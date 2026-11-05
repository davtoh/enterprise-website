import json
from decimal import Decimal
import pytest
from django.core import mail
from django.urls import reverse

from crm.models import (
    Company,
    Contact,
    Lead,
    LeadStage,
    LeadSource,
    InteractionType,
    EmailSequence,
    EmailDeliveryLog,
    EmailDeliveryStatus,
    Segment,
)
from crm.plugin import CRMPlugin


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


def _create_sample_lead(client, contact_pk, company_pk):
    create_url = reverse("crm:lead_create")
    post_data = {
        "title": "New Enterprise License",
        "contact": contact_pk,
        "company": company_pk,
        "stage": LeadStage.NEW,
        "source": LeadSource.WEBSITE,
        "value": "25000.00",
        "notes": "Interested in 50 seats",
    }
    resp = client.post(create_url, post_data)
    assert resp.status_code == 302
    lead = Lead.objects.get(title="New Enterprise License")
    assert lead.value == Decimal("25000.00")
    return lead, post_data


@pytest.mark.django_db
def test_lead_crud_views(client, auth_user, test_contact, test_company):
    client.force_login(auth_user)

    # Create Lead
    created_lead, post_data = _create_sample_lead(client, test_contact.pk, test_company.pk)

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
    client.post(update_url, {**post_data, "title": "New Enterprise License (50 Seats)"})
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
