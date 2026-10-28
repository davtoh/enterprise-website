import logging
from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


def send_visitor_arrival_notification(contact, access_log) -> bool:
    """
    Dispatches automated bilingual host arrival notification (English & Spanish)
    when an authorized or restricted entity passes a physical access gate.
    """
    if not contact or not access_log:
        return False

    recipient_email = None
    if hasattr(contact, "assigned_to") and contact.assigned_to and contact.assigned_to.email:
        recipient_email = contact.assigned_to.email
    elif getattr(settings, "SECURITY_DISPATCH_EMAIL", None):
        recipient_email = settings.SECURITY_DISPATCH_EMAIL
    elif getattr(settings, "DEFAULT_FROM_EMAIL", None):
        recipient_email = settings.DEFAULT_FROM_EMAIL

    if not recipient_email:
        recipient_email = "security-desk@example.com"

    company_name = contact.company.name if contact.company else "Independent / Guest"
    site_name = access_log.site.name if access_log.site else "Facility Gate"
    direction_display = access_log.get_direction_display()
    method_display = access_log.get_verification_method_display()
    status_str = "GRANTED / AUTORIZADO" if access_log.access_granted else f"DENIED / DENEGADO ({access_log.denial_reason})"

    subject = f"[Security Hub] Arrival Notification: {contact.full_name} @ {site_name}"

    body = f"""================================================================================
ENTERPRISE SECURITY OPERATIONS CENTER - ACCESS NOTIFICATION
CENTRO DE OPERACIONES DE SEGURIDAD - NOTIFICACIÓN DE ACCESO
================================================================================

[ENGLISH]
Visitor / Staff Access Event Logged:
- Name: {contact.full_name}
- Clearance Level: {contact.get_security_clearance_display()}
- Company: {company_name}
- Facility / Site: {site_name}
- Gate / Camera: {access_log.camera_id}
- Verification Method: {method_display}
- Direction: {direction_display}
- Status: {status_str}
- Timestamp (UTC): {access_log.timestamp:%Y-%m-%d %H:%M:%S}

--------------------------------------------------------------------------------
[ESPAÑOL]
Registro de Acceso de Visitante / Personal:
- Nombre: {contact.full_name}
- Nivel de Autorización: {contact.get_security_clearance_display()}
- Empresa: {company_name}
- Instalación / Sitio: {site_name}
- Puerta / Cámara: {access_log.camera_id}
- Método de Verificación: {method_display}
- Dirección: {direction_display}
- Estado: {status_str}
- Fecha y Hora (UTC): {access_log.timestamp:%Y-%m-%d %H:%M:%S}

================================================================================
Enterprise Website Intelligent Tracker Hub Integration
"""

    try:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@enterprise-website.local")
        send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        logger.info(
            "Visitor arrival notification sent successfully to %s for contact %s (%s)",
            recipient_email,
            contact.full_name,
            access_log.camera_id,
        )
        return True
    except Exception as exc:
        logger.warning(
            "Failed to dispatch arrival email to %s: %s",
            recipient_email,
            exc,
        )
        return False
