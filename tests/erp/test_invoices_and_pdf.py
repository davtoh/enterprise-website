import datetime
from decimal import Decimal
import pytest
from django.core import mail
from django.urls import reverse

from erp.models import Invoice, InvoiceItem, InvoiceStatus
from erp.pdf import generate_invoice_pdf
from erp.tasks import send_invoice_email


@pytest.mark.django_db
def test_invoice_and_item_totals_calculation(test_invoice):
    # Initial: 2 units @ $4500 = $9,000 subtotal
    # Tax: 10% of $9000 = $900
    # Discount: $100
    # Total: $9,000 + $900 - $100 = $9,800
    test_invoice.refresh_from_db()
    assert test_invoice.subtotal == Decimal("9000.00")
    assert test_invoice.tax_amount == Decimal("900.00")
    assert test_invoice.total_amount == Decimal("9800.00")
    assert test_invoice.invoice_number.startswith("INV-")

    # Add second item
    InvoiceItem.objects.create(
        invoice=test_invoice,
        description="Warranty Support Plan",
        quantity=Decimal("1.00"),
        unit_price=Decimal("1000.00"),
    )
    test_invoice.refresh_from_db()
    # New subtotal: $10,000
    # Tax: 10% = $1,000
    # Total: $10,000 + $1,000 - $100 = $10,900
    assert test_invoice.subtotal == Decimal("10000.00")
    assert test_invoice.tax_amount == Decimal("1000.00")
    assert test_invoice.total_amount == Decimal("10900.00")


@pytest.mark.django_db
def test_generate_invoice_pdf(test_invoice):
    pdf_bytes = generate_invoice_pdf(test_invoice)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")


@pytest.mark.django_db
def test_send_invoice_email_task(test_invoice):
    assert test_invoice.status == InvoiceStatus.DRAFT

    result = send_invoice_email(test_invoice.pk)
    assert result["status"] == "success"
    assert result["recipient"] == test_invoice.customer_email

    # Check status transitioned to SENT
    test_invoice.refresh_from_db()
    assert test_invoice.status == InvoiceStatus.SENT

    # Check mail outbox
    assert len(mail.outbox) >= 1
    sent_mail = mail.outbox[-1]
    assert test_invoice.customer_email in sent_mail.to
    assert len(sent_mail.attachments) == 1
    assert sent_mail.attachments[0][0].endswith(".pdf")


def _test_invoice_read_and_status_views(client, test_invoice):
    """Test read, pdf, status update, and email endpoints."""
    # 1. Invoice list
    list_resp = client.get(reverse("erp:invoice_list"))
    assert list_resp.status_code == 200
    assert test_invoice.invoice_number in list_resp.content.decode()

    # 2. Invoice detail
    detail_resp = client.get(reverse("erp:invoice_detail", kwargs={"pk": test_invoice.pk}))
    assert detail_resp.status_code == 200
    assert test_invoice.customer_name in detail_resp.content.decode()

    # 3. Invoice PDF view
    pdf_resp = client.get(reverse("erp:invoice_pdf", kwargs={"pk": test_invoice.pk}))
    assert pdf_resp.status_code == 200
    assert pdf_resp["Content-Type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF")

    # 4. Status update
    status_resp = client.post(
        reverse("erp:invoice_status_update", kwargs={"pk": test_invoice.pk, "new_status": "PAID"})
    )
    assert status_resp.status_code == 302
    test_invoice.refresh_from_db()
    assert test_invoice.status == InvoiceStatus.PAID

    # 5. Email invoice view
    email_resp = client.post(reverse("erp:invoice_send_email", kwargs={"pk": test_invoice.pk}))
    assert email_resp.status_code == 302


def _test_invoice_create_view(client):
    """Test invoice create endpoint with line items."""
    assert client.get(reverse("erp:invoice_create")).status_code == 200

    post_data = {
        "customer_name": "Nexus Corp",
        "customer_email": "billing@nexuscorp.local",
        "customer_address": "123 Tech Way",
        "issue_date": str(datetime.date.today()),
        "due_date": str(datetime.date.today() + datetime.timedelta(days=15)),
        "status": InvoiceStatus.DRAFT,
        "tax_rate": "5.00",
        "discount_amount": "0.00",
        "notes": "Net 15",
        "items-TOTAL_FORMS": "1",
        "items-INITIAL_FORMS": "0",
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
        "items-0-description": "Engineering Consulting",
        "items-0-quantity": "10.00",
        "items-0-unit_price": "150.00",
    }
    assert client.post(reverse("erp:invoice_create"), post_data).status_code == 302
    created = Invoice.objects.get(customer_name="Nexus Corp")
    assert created.total_amount == Decimal("1575.00")
    return created


def _test_invoice_update_delete_views(client, invoice):
    """Test invoice update and delete endpoints."""
    assert client.get(reverse("erp:invoice_update", kwargs={"pk": invoice.pk})).status_code == 200
    item_id = invoice.items.first().pk
    update_data = {
        "customer_name": "Nexus Corporation Global",
        "customer_email": "billing@nexuscorp.local",
        "customer_address": "123 Tech Way",
        "issue_date": str(datetime.date.today()),
        "due_date": str(datetime.date.today() + datetime.timedelta(days=15)),
        "status": InvoiceStatus.DRAFT,
        "tax_rate": "5.00",
        "discount_amount": "0.00",
        "items-TOTAL_FORMS": "1",
        "items-INITIAL_FORMS": "1",
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
        "items-0-id": str(item_id),
        "items-0-invoice": str(invoice.pk),
        "items-0-description": "Engineering Consulting",
        "items-0-quantity": "10.00",
        "items-0-unit_price": "150.00",
    }
    assert client.post(reverse("erp:invoice_update", kwargs={"pk": invoice.pk}), update_data).status_code == 302
    invoice.refresh_from_db()
    assert invoice.customer_name == "Nexus Corporation Global"

    del_resp = client.post(reverse("erp:invoice_delete", kwargs={"pk": invoice.pk}))
    assert del_resp.status_code == 302
    assert not Invoice.objects.filter(pk=invoice.pk).exists()


@pytest.mark.django_db
def test_invoice_views(client, auth_user, test_invoice):
    client.force_login(auth_user)
    _test_invoice_read_and_status_views(client, test_invoice)
    created = _test_invoice_create_view(client)
    _test_invoice_update_delete_views(client, created)

