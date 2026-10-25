import datetime
from decimal import Decimal
from django.conf import settings
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth
from django.template import Context, Template
from django.urls import reverse
from django.utils import timezone


def auto_enroll_lead_in_sequences(lead):
    """
    Checks active EmailSequences whose trigger_stage matches the lead's current stage,
    and automatically enrolls the primary contact.
    """
    from .models import EmailSequence, SequenceEnrollment, SequenceEnrollmentStatus, InteractionLog, InteractionType

    if not lead or not lead.contact or not lead.stage:
        return []

    if not lead.contact.is_subscribed:
        return []

    matching_sequences = EmailSequence.objects.filter(is_active=True, trigger_stage=lead.stage)
    enrollments_created = []

    for seq in matching_sequences:
        # Avoid duplicate active enrollment in same sequence
        exists = SequenceEnrollment.objects.filter(
            sequence=seq,
            contact=lead.contact,
            lead=lead,
            status=SequenceEnrollmentStatus.ACTIVE,
        ).exists()

        if not exists:
            enrollment = SequenceEnrollment.objects.create(
                sequence=seq,
                contact=lead.contact,
                lead=lead,
                current_step_number=1,
                status=SequenceEnrollmentStatus.ACTIVE,
                next_send_at=timezone.now(),
            )
            enrollments_created.append(enrollment)

            InteractionLog.objects.create(
                lead=lead,
                contact=lead.contact,
                interaction_type=InteractionType.SEQUENCE_STEP,
                summary=f"Auto-enrolled in sequence '{seq.name}'",
                details=f"Lead moved into stage '{lead.get_stage_display()}'. First email scheduled.",
            )

    return enrollments_created


def render_email_content(step, contact, lead=None, tracking_token=None, base_url=""):
    """
    Renders an EmailStep's subject and body using Django's template engine
    with fallback string substitution.
    """
    company = contact.company or (lead.company if lead else None)

    tracking_pixel_html = ""
    if tracking_token:
        tracking_url = f"{base_url.rstrip('/')}{reverse('crm:email_tracking_pixel', kwargs={'token': tracking_token})}"
        tracking_pixel_html = f'<img src="{tracking_url}" width="1" height="1" alt="" border="0" style="display:none !important;" />'

    context_dict = {
        "contact": {
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "full_name": contact.full_name,
            "email": contact.email,
            "phone": contact.phone,
            "job_title": contact.job_title,
        },
        "company": {
            "name": company.name if company else "",
            "industry": company.industry if company else "",
            "website": company.website if company else "",
        },
        "lead": {
            "title": lead.title if lead else "",
            "value": str(lead.value) if lead else "0",
            "stage": lead.get_stage_display() if lead else "",
        },
        "tracking_pixel": tracking_pixel_html,
    }

    try:
        subject_tmpl = Template(step.subject)
        rendered_subject = subject_tmpl.render(Context(context_dict))
    except Exception:
        rendered_subject = step.subject

    try:
        body_tmpl = Template(step.body_template)
        rendered_body = body_tmpl.render(Context(context_dict))
    except Exception:
        rendered_body = step.body_template

    if tracking_pixel_html and tracking_pixel_html not in rendered_body:
        rendered_body += f"\n\n{tracking_pixel_html}"

    return rendered_subject, rendered_body


def get_crm_analytics_data():
    """
    Computes comprehensive CRM metrics for the analytics dashboard and Chart.js:
    - Lead Funnel Conversion counts
    - Monthly New Contacts (past 6 months)
    - Email Deliveries & Open Rate
    - Revenue Pipeline Value by Stage
    """
    from .models import (
        Lead,
        LeadStage,
        Contact,
        EmailDeliveryLog,
        EmailDeliveryStatus,
    )

    # 1. Lead Funnel Conversion
    stage_counts = {stage.value: 0 for stage in LeadStage}
    lead_aggregates = Lead.objects.values("stage").annotate(count=Count("id"))
    for item in lead_aggregates:
        if item["stage"] in stage_counts:
            stage_counts[item["stage"]] = item["count"]

    funnel_labels = [stage.label for stage in LeadStage]
    funnel_values = [stage_counts[stage.value] for stage in LeadStage]

    # 2. Pipeline Revenue by Stage
    revenue_by_stage = {stage.value: Decimal("0.00") for stage in LeadStage}
    rev_aggregates = Lead.objects.values("stage").annotate(total_val=Sum("value"))
    for item in rev_aggregates:
        if item["stage"] in revenue_by_stage:
            revenue_by_stage[item["stage"]] = item["total_val"] or Decimal("0.00")

    pipeline_values = [float(revenue_by_stage[stage.value]) for stage in LeadStage]

    # 3. Monthly New Contacts (last 6 months)
    six_months_ago = timezone.now() - datetime.timedelta(days=180)
    monthly_contacts_qs = (
        Contact.objects.filter(created_at__gte=six_months_ago)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )
    month_labels = []
    month_counts = []
    for entry in monthly_contacts_qs:
        m = entry["month"]
        if m:
            month_labels.append(m.strftime("%b %Y"))
            month_counts.append(entry["count"])

    if not month_labels:
        # Default empty window representation
        now = timezone.now()
        month_labels = [now.strftime("%b %Y")]
        month_counts = [Contact.objects.count()]

    # 4. Email Delivery & Open Rates
    total_emails_sent = EmailDeliveryLog.objects.filter(
        status__in=[EmailDeliveryStatus.SENT, EmailDeliveryStatus.OPENED]
    ).count()
    total_emails_opened = EmailDeliveryLog.objects.filter(
        status=EmailDeliveryStatus.OPENED
    ).count()
    total_emails_failed = EmailDeliveryLog.objects.filter(
        status=EmailDeliveryStatus.FAILED
    ).count()

    open_rate = (
        round((total_emails_opened / total_emails_sent) * 100, 1)
        if total_emails_sent > 0
        else 0.0
    )

    # 5. High-level KPIs
    total_leads = Lead.objects.count()
    won_leads = Lead.objects.filter(stage=LeadStage.WON).count()
    win_rate = round((won_leads / total_leads) * 100, 1) if total_leads > 0 else 0.0
    total_pipeline_val = Lead.objects.filter(
        ~Q(stage=LeadStage.LOST)
    ).aggregate(total=Sum("value"))["total"] or Decimal("0.00")

    return {
        "kpi": {
            "total_leads": total_leads,
            "won_leads": won_leads,
            "win_rate": win_rate,
            "total_contacts": Contact.objects.count(),
            "total_pipeline_val": float(total_pipeline_val),
            "emails_sent": total_emails_sent,
            "emails_opened": total_emails_opened,
            "emails_failed": total_emails_failed,
            "email_open_rate": open_rate,
        },
        "funnel": {
            "labels": [str(lbl) for lbl in funnel_labels],
            "data": funnel_values,
        },
        "pipeline_revenue": {
            "labels": [str(lbl) for lbl in funnel_labels],
            "data": pipeline_values,
        },
        "monthly_contacts": {
            "labels": month_labels,
            "data": month_counts,
        },
        "email_stats": {
            "labels": ["Opened", "Unopened", "Failed"],
            "data": [
                total_emails_opened,
                max(0, total_emails_sent - total_emails_opened),
                total_emails_failed,
            ],
        },
    }
