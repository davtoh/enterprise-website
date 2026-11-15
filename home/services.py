from django.db import transaction

from crm.models import Contact, InteractionLog, InteractionType, Lead, LeadSource
from todo.models import Todo


def _split_contact_name(full_name: str) -> tuple[str, str]:
    """Split a full name into (first_name, last_name) capped to Contact field lengths."""
    parts = full_name.split(None, 1)
    first_name = (parts[0] if parts else "")[:120]
    last_name = (parts[1] if len(parts) > 1 else "")[:120]
    return first_name, last_name


def ingest_website_contact_submission(
    name: str,
    email: str,
    subject: str,
    message: str,
) -> tuple[Contact, Lead, InteractionLog, Todo]:
    """Atomically record a website contact submission as a CRM contact, lead, interaction, and follow-up todo."""
    clean_name = name.strip()
    clean_email = email.strip().lower()
    clean_subject = subject.strip()
    clean_message = message.strip()
    first_name, last_name = _split_contact_name(clean_name)
    lead_title = (clean_subject or f"Website Inquiry from {clean_name}")[:255]

    with transaction.atomic():
        contact, _created = Contact.objects.update_or_create(
            email=clean_email,
            defaults={"first_name": first_name, "last_name": last_name},
        )
        lead = Lead.objects.create(
            title=lead_title,
            contact=contact,
            source=LeadSource.WEBSITE,
            notes=clean_message,
        )
        interaction = InteractionLog.objects.create(
            lead=lead,
            contact=contact,
            interaction_type=InteractionType.NOTE,
            summary=f"Website contact form: {lead_title}"[:255],
            details=clean_message,
        )
        followup_todo = Todo.objects.create(
            title=f"Follow up with {clean_name}: {lead_title}"[:500],
            text=f"Contact: {clean_name} <{clean_email}>\nSubject: {clean_subject or '(No subject)'}\n\n{clean_message}",
        )

    return contact, lead, interaction, followup_todo
