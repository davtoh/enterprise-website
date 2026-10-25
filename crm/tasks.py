import datetime
import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from task_runner.base import TrackedTask
from .utils import render_email_content

logger = logging.getLogger(__name__)


@shared_task(base=TrackedTask, bind=True, name="crm.process_email_sequences")
def process_email_sequences(self):
    """
    Background worker task that evaluates all active email sequence enrollments
    due for dispatch, renders templates, sends emails via Django mail backend,
    updates delivery logs, and advances sequence steps.
    """
    from .models import (
        SequenceEnrollment,
        SequenceEnrollmentStatus,
        EmailStep,
        EmailDeliveryLog,
        EmailDeliveryStatus,
        InteractionLog,
        InteractionType,
    )

    now = timezone.now()
    due_enrollments = SequenceEnrollment.objects.filter(
        status=SequenceEnrollmentStatus.ACTIVE,
        next_send_at__lte=now,
    ).select_related("sequence", "contact", "lead")

    total_due = due_enrollments.count()
    if hasattr(self, "update_job_progress"):
        self.update_job_progress(10, f"Found {total_due} sequence enrollments due for processing.")

    processed = 0
    sent_count = 0

    for enrollment in due_enrollments:
        processed += 1
        seq = enrollment.sequence
        contact = enrollment.contact
        lead = enrollment.lead

        # Verify sequence is still active and contact is subscribed
        if not seq.is_active or not contact.is_subscribed:
            enrollment.status = SequenceEnrollmentStatus.PAUSED
            enrollment.save(update_fields=["status"])
            continue

        # Fetch current step
        step = EmailStep.objects.filter(
            sequence=seq,
            step_number=enrollment.current_step_number,
        ).first()

        if not step:
            # Sequence has finished all steps
            enrollment.status = SequenceEnrollmentStatus.COMPLETED
            enrollment.completed_at = timezone.now()
            enrollment.save(update_fields=["status", "completed_at"])

            InteractionLog.objects.create(
                lead=lead,
                contact=contact,
                interaction_type=InteractionType.SEQUENCE_STEP,
                summary=f"Sequence completed: '{seq.name}'",
                details=f"Contact finished all steps in drip sequence '{seq.name}'.",
            )
            continue

        # Prepare delivery log
        delivery = EmailDeliveryLog.objects.create(
            enrollment=enrollment,
            step=step,
            contact=contact,
            lead=lead,
            recipient_email=contact.email,
            subject=step.subject,
            status=EmailDeliveryStatus.SENT,
        )

        # Render email content
        base_url = getattr(settings, "SITE_URL", "http://localhost:8000")
        rendered_subject, rendered_body = render_email_content(
            step=step,
            contact=contact,
            lead=lead,
            tracking_token=delivery.tracking_token,
            base_url=base_url,
        )
        delivery.subject = rendered_subject

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "crm@example.com")
        try:
            send_mail(
                subject=rendered_subject,
                message=rendered_body,
                from_email=from_email,
                recipient_list=[contact.email],
                html_message=rendered_body,
                fail_silently=False,
            )
            delivery.status = EmailDeliveryStatus.SENT
            delivery.save(update_fields=["status", "subject"])
            sent_count += 1

            # Log interaction
            InteractionLog.objects.create(
                lead=lead,
                contact=contact,
                interaction_type=InteractionType.SEQUENCE_STEP,
                summary=f"Drip Email Sent: {rendered_subject}",
                details=f"Step #{step.step_number} of sequence '{seq.name}' dispatched to {contact.email}.",
            )

            # Advance to next step or complete
            next_step = EmailStep.objects.filter(
                sequence=seq,
                step_number=enrollment.current_step_number + 1,
            ).first()

            if next_step:
                enrollment.current_step_number = next_step.step_number
                enrollment.next_send_at = timezone.now() + datetime.timedelta(days=next_step.delay_days)
                enrollment.save(update_fields=["current_step_number", "next_send_at"])
            else:
                enrollment.status = SequenceEnrollmentStatus.COMPLETED
                enrollment.completed_at = timezone.now()
                enrollment.save(update_fields=["status", "completed_at"])

        except Exception as exc:
            logger.exception("Failed to send sequence email to %s: %s", contact.email, exc)
            delivery.status = EmailDeliveryStatus.FAILED
            delivery.error_message = str(exc)
            delivery.save(update_fields=["status", "error_message"])

        if hasattr(self, "update_job_progress") and total_due > 0:
            percent = int(10 + (processed / total_due) * 85)
            self.update_job_progress(percent, f"Processed {processed}/{total_due} enrollments ({sent_count} sent).")

    summary_msg = f"Finished sequence processing: {processed} evaluated, {sent_count} emails sent."
    if hasattr(self, "update_job_progress"):
        self.update_job_progress(100, summary_msg)

    return {"processed": processed, "sent": sent_count}


@shared_task(base=TrackedTask, bind=True, name="crm.send_segment_broadcast")
def send_segment_broadcast(self, segment_id: int, subject: str, message: str, sender_user_id=None):
    """
    Broadcasts an email campaign to all subscribed contacts in a Customer Segment.
    """
    from .models import Segment, EmailDeliveryLog, EmailDeliveryStatus, InteractionLog, InteractionType
    from django.contrib.auth import get_user_model

    segment = Segment.objects.get(pk=segment_id)
    contacts = segment.get_matching_contacts().filter(is_subscribed=True)
    total_contacts = contacts.count()

    if hasattr(self, "update_job_progress"):
        self.update_job_progress(5, f"Starting broadcast to {total_contacts} contacts in segment '{segment.name}'")

    sent_count = 0
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "crm@example.com")
    base_url = getattr(settings, "SITE_URL", "http://localhost:8000")

    User = get_user_model()
    sender_user = User.objects.filter(pk=sender_user_id).first() if sender_user_id else None

    for idx, contact in enumerate(contacts, 1):
        delivery = EmailDeliveryLog.objects.create(
            contact=contact,
            recipient_email=contact.email,
            subject=subject,
            status=EmailDeliveryStatus.SENT,
        )

        tracking_url = f"{base_url.rstrip('/')}/crm/track/{delivery.tracking_token}.png"
        pixel_tag = f'<img src="{tracking_url}" width="1" height="1" alt="" border="0" style="display:none !important;" />'
        full_html = f"{message}\n\n{pixel_tag}"

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=[contact.email],
                html_message=full_html,
                fail_silently=False,
            )
            delivery.status = EmailDeliveryStatus.SENT
            delivery.save(update_fields=["status"])
            sent_count += 1

            InteractionLog.objects.create(
                contact=contact,
                user=sender_user,
                interaction_type=InteractionType.BROADCAST,
                summary=f"Broadcast received: {subject}",
                details=f"Campaign sent via segment '{segment.name}'.",
            )
        except Exception as exc:
            delivery.status = EmailDeliveryStatus.FAILED
            delivery.error_message = str(exc)
            delivery.save(update_fields=["status", "error_message"])

        if hasattr(self, "update_job_progress") and total_contacts > 0:
            pct = int(5 + (idx / total_contacts) * 90)
            self.update_job_progress(pct, f"Sent broadcast {idx}/{total_contacts}")

    result_msg = f"Completed broadcast to segment '{segment.name}': {sent_count}/{total_contacts} sent."
    if hasattr(self, "update_job_progress"):
        self.update_job_progress(100, result_msg)

    return {"sent_count": sent_count, "total_contacts": total_contacts}
