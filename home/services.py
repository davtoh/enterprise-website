from django.apps import apps
from django.db import transaction


def _load_crm_models():
    """Return CRM models if `crm` is installed and importable, else None."""
    if not apps.is_installed("crm"):
        return None
    try:
        from crm.models import Contact, InteractionLog, InteractionType, Lead, LeadSource
    except ImportError:
        return None
    return Contact, InteractionLog, InteractionType, Lead, LeadSource


def _load_todo_model():
    """Return Todo model if `todo` is installed and importable, else None."""
    if not apps.is_installed("todo"):
        return None
    try:
        from todo.models import Todo
    except ImportError:
        return None
    return Todo


def _split_contact_name(full_name: str) -> tuple[str, str]:
    """Split a full name into (first_name, last_name) capped to Contact field lengths."""
    parts = full_name.split(None, 1)
    first_name = (parts[0] if parts else "")[:120]
    last_name = (parts[1] if len(parts) > 1 else "")[:120]
    return first_name, last_name


def _upsert_contact_by_email(clean_email: str, first_name: str, last_name: str, contact_model=None):
    """Match an existing Contact case-insensitively before creating a new normalized row."""
    if contact_model is None:
        crm_models = _load_crm_models()
        if crm_models is None:
            return None
        contact_model = crm_models[0]

    contact = contact_model.objects.filter(email__iexact=clean_email).order_by("id").first()
    if contact is not None:
        contact.first_name = first_name
        contact.last_name = last_name
        contact.save(update_fields=["first_name", "last_name"])
        return contact

    contact, _created = contact_model.objects.update_or_create(
        email=clean_email,
        defaults={"first_name": first_name, "last_name": last_name},
    )
    return contact


def _record_crm_lead(crm_models, clean_name: str, clean_email: str, clean_message: str, lead_title: str):
    """Create CRM contact, lead, and interaction log when the `crm` app is installed."""
    if crm_models is None:
        return None, None, None
    contact_model, interaction_model, interaction_type, lead_model, lead_source = crm_models
    first_name, last_name = _split_contact_name(clean_name)
    contact = _upsert_contact_by_email(clean_email, first_name, last_name, contact_model=contact_model)
    lead = lead_model.objects.create(
        title=lead_title,
        contact=contact,
        source=lead_source.WEBSITE,
        notes=clean_message,
    )
    interaction = interaction_model.objects.create(
        lead=lead,
        contact=contact,
        interaction_type=interaction_type.NOTE,
        summary=f"Website contact form: {lead_title}"[:255],
        details=clean_message,
    )
    return contact, lead, interaction


def _create_followup_todo(
    clean_name: str,
    clean_email: str,
    clean_subject: str,
    clean_message: str,
    lead_title: str,
    lead=None,
):
    """Create a follow-up Todo item when the `todo` app is installed."""
    todo_model = _load_todo_model()
    if todo_model is None:
        return None
    kwargs = {
        "title": f"Follow up with {clean_name}: {lead_title}"[:500],
        "text": f"Contact: {clean_name} <{clean_email}>\nSubject: {clean_subject or '(No subject)'}\n\n{clean_message}",
    }
    if lead is not None:
        kwargs["content_object"] = lead
    return todo_model.objects.create(**kwargs)


def ingest_website_contact_submission(
    name: str,
    email: str,
    subject: str,
    message: str,
) -> tuple:
    """Atomically record a website contact submission as CRM lead and follow-up todo when installed."""
    clean_name = name.strip()
    clean_email = email.strip().lower()
    clean_subject = subject.strip()
    clean_message = message.strip()
    lead_title = (clean_subject or f"Website Inquiry from {clean_name}")[:255]
    crm_models = _load_crm_models()

    with transaction.atomic():
        contact, lead, interaction = _record_crm_lead(
            crm_models, clean_name, clean_email, clean_message, lead_title
        )
        followup_todo = _create_followup_todo(
            clean_name, clean_email, clean_subject, clean_message, lead_title, lead=lead
        )

    return contact, lead, interaction, followup_todo
