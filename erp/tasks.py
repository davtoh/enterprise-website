import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import F
from django.utils.translation import gettext as _
from task_runner.base import TrackedTask
from .models import Product, Invoice, InvoiceStatus
from .pdf import generate_invoice_pdf

logger = logging.getLogger(__name__)


@shared_task(base=TrackedTask, bind=True, name="erp.check_low_stock_alerts")
def check_low_stock_alerts(self):
    """
    Periodic Celery Beat task that evaluates inventory levels against configured
    reorder thresholds, sends alert notifications, and reports status.
    """
    if hasattr(self, "update_job_progress"):
        self.update_job_progress(10, "Evaluating inventory stock thresholds...")

    low_stock_products = Product.objects.filter(
        is_active=True,
        current_stock__lte=F("reorder_threshold"),
    ).select_related("category")

    count = low_stock_products.count()
    items_summary = [
        {
            "sku": p.sku,
            "name": p.name,
            "current_stock": p.current_stock,
            "reorder_threshold": p.reorder_threshold,
        }
        for p in low_stock_products
    ]

    if count > 0:
        logger.warning(
            "Low-stock alert triggered: %d product(s) below reorder threshold: %s",
            count,
            [p["sku"] for p in items_summary],
        )

        admin_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@enterprise.local")
        body = (
            f"Automated ERP Inventory Alert:\n\n"
            f"{count} product(s) have fallen below their configured reorder threshold.\n\n"
        )
        for item in items_summary:
            body += (
                f"- [{item['sku']}] {item['name']}: Current Stock = {item['current_stock']} "
                f"(Threshold = {item['reorder_threshold']})\n"
            )
        body += "\nPlease review the inventory dashboard at /erp/inventory/ to place reorders."

        try:
            msg = EmailMessage(
                subject=f"[ERP Alert] {count} Low-Stock Products Detected",
                body=body,
                from_email=admin_email,
                to=[admin_email],
            )
            msg.send(fail_silently=True)
        except Exception as exc:
            logger.error("Failed to send low stock alert email: %s", exc)

    if hasattr(self, "update_job_progress"):
        self.update_job_progress(100, f"Completed low-stock check. {count} item(s) flagged.")

    return {
        "status": "success",
        "low_stock_count": count,
        "flagged_items": items_summary,
    }


@shared_task(base=TrackedTask, bind=True, name="erp.send_invoice_email")
def send_invoice_email(self, invoice_id: int):
    """
    Dispatches a generated PDF invoice directly to the customer's email address
    and updates the invoice status to SENT if it was in DRAFT status.
    """
    if hasattr(self, "update_job_progress"):
        self.update_job_progress(10, f"Preparing PDF for invoice #{invoice_id}...")

    try:
        invoice = Invoice.objects.get(pk=invoice_id)
    except Invoice.DoesNotExist:
        error_msg = f"Invoice with ID {invoice_id} not found."
        logger.error(error_msg)
        if hasattr(self, "update_job_progress"):
            self.update_job_progress(100, error_msg)
        return {"status": "error", "message": error_msg}

    # Generate PDF attachment
    pdf_bytes = generate_invoice_pdf(invoice)

    if hasattr(self, "update_job_progress"):
        self.update_job_progress(50, f"PDF generated. Sending email to {invoice.customer_email}...")

    subject = f"Invoice {invoice.invoice_number} from Enterprise Systems"
    body = (
        f"Dear {invoice.customer_name},\n\n"
        f"Please find attached your invoice {invoice.invoice_number} for the amount of ${invoice.total_amount:.2f}.\n"
        f"Due Date: {invoice.due_date.strftime('%B %d, %Y')}\n\n"
        f"Thank you for your business.\n\n"
        f"Sincerely,\n"
        f"Enterprise ERP Team"
    )

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "billing@enterprise.local")
    msg = EmailMessage(
        subject=subject,
        body=body,
        from_email=from_email,
        to=[invoice.customer_email],
    )
    msg.attach(f"{invoice.invoice_number}.pdf", pdf_bytes, "application/pdf")
    msg.send(fail_silently=False)

    # Transition status from DRAFT to SENT
    if invoice.status == InvoiceStatus.DRAFT:
        invoice.status = InvoiceStatus.SENT
        invoice.save(update_fields=["status", "updated_at"])

    if hasattr(self, "update_job_progress"):
        self.update_job_progress(100, f"Invoice {invoice.invoice_number} emailed successfully.")

    return {
        "status": "success",
        "invoice_id": invoice.pk,
        "invoice_number": invoice.invoice_number,
        "recipient": invoice.customer_email,
    }
