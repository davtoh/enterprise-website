import datetime
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .catalog import Product


class InvoiceStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    SENT = "SENT", _("Sent / Issued")
    PAID = "PAID", _("Paid")
    OVERDUE = "OVERDUE", _("Overdue")
    CANCELLED = "CANCELLED", _("Cancelled")


class Invoice(models.Model):
    """Commercial invoice billing customers for products or services."""

    invoice_number = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        verbose_name=_("Invoice Number"),
    )
    crm_company = models.ForeignKey(
        "crm.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="erp_invoices",
        verbose_name=_("CRM Company"),
    )
    crm_contact = models.ForeignKey(
        "crm.Contact",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="erp_invoices",
        verbose_name=_("CRM Contact"),
    )
    customer_name = models.CharField(max_length=200, blank=True, verbose_name=_("Customer / Client Name"))
    customer_email = models.EmailField(blank=True, verbose_name=_("Customer Email"))
    customer_address = models.TextField(blank=True, verbose_name=_("Customer Address"))
    issue_date = models.DateField(default=datetime.date.today, verbose_name=_("Issue Date"))
    due_date = models.DateField(verbose_name=_("Due Date"))
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
        verbose_name=_("Status"),
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Subtotal"),
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Tax Rate (%)"),
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Tax Amount"),
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Discount Amount"),
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Total Amount"),
    )
    notes = models.TextField(blank=True, verbose_name=_("Terms / Notes"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Created By"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")
        ordering = ["-issue_date", "-id"]

    def __str__(self):
        return f"{self.invoice_number or f'INV-#{self.pk}'} - {self.customer_name} ({self.get_status_display()})"

    @staticmethod
    def _format_company_address(company) -> str:
        parts = [company.address, company.city, company.country]
        return ", ".join(part.strip() for part in parts if part and part.strip())

    def _backfill_customer_from_crm(self):
        """Backfill blank customer metadata from linked CRM contact or company."""
        contact = self.crm_contact
        company = self.crm_company or (contact.company if contact else None)

        if contact and not self.crm_company and contact.company_id:
            self.crm_company = contact.company

        if not self.customer_name:
            if contact and company:
                self.customer_name = f"{contact.full_name} ({company.name})"
            elif contact:
                self.customer_name = contact.full_name
            elif company:
                self.customer_name = company.name

        if not self.customer_email and contact and contact.email:
            self.customer_email = contact.email

        if not self.customer_address and company:
            self.customer_address = self._format_company_address(company)

    def save(self, *args, **kwargs):
        self._backfill_customer_from_crm()
        if not self.due_date:
            self.due_date = self.issue_date + datetime.timedelta(days=30)
        if not self.invoice_number:
            year_month = timezone.now().strftime("%Y%m")
            count = Invoice.objects.filter(invoice_number__startswith=f"INV-{year_month}").count() + 1
            candidate = f"INV-{year_month}-{count:04d}"
            while Invoice.objects.filter(invoice_number=candidate).exists():
                count += 1
                candidate = f"INV-{year_month}-{count:04d}"
            self.invoice_number = candidate
        super().save(*args, **kwargs)

    def recalculate_totals(self):
        """Recalculate subtotal, tax amount, and final total based on related items."""
        items = list(self.items.all())
        subtotal = sum((item.total_price for item in items), Decimal("0.00"))
        tax_amount = (subtotal * (self.tax_rate / Decimal("100.00"))).quantize(Decimal("0.01"))
        total_amount = max(Decimal("0.00"), subtotal + tax_amount - self.discount_amount)

        self.subtotal = subtotal
        self.tax_amount = tax_amount
        self.total_amount = total_amount
        self.save(update_fields=["subtotal", "tax_amount", "total_amount", "updated_at"])


class InvoiceItem(models.Model):
    """Line item in an invoice."""

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Invoice"),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_items",
        verbose_name=_("Product"),
    )
    description = models.CharField(max_length=255, verbose_name=_("Item Description"))
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("1.00"),
        verbose_name=_("Quantity"),
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Unit Price"),
    )
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Line Total"),
    )

    class Meta:
        verbose_name = _("Invoice Item")
        verbose_name_plural = _("Invoice Items")

    def __str__(self):
        return f"{self.description} ({self.quantity} @ {self.unit_price})"

    def save(self, *args, **kwargs):
        self.total_price = (self.quantity * self.unit_price).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)
        if self.invoice_id:
            self.invoice.recalculate_totals()

    def delete(self, *args, **kwargs):
        invoice = self.invoice
        super().delete(*args, **kwargs)
        if invoice:
            invoice.recalculate_totals()
