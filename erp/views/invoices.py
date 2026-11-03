import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import DeleteView, DetailView, ListView

from erp.forms import InvoiceForm, InvoiceItemFormSet
from erp.models import Invoice, InvoiceStatus
from erp.pdf import generate_invoice_pdf
from erp.tasks import send_invoice_email

logger = logging.getLogger(__name__)


class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = "erp/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 15

    def get_queryset(self):
        qs = Invoice.objects.order_by("-issue_date", "-id")
        status = self.request.GET.get("status", "").strip()
        q = self.request.GET.get("q", "").strip()
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(Q(invoice_number__icontains=q) | Q(customer_name__icontains=q) | Q(customer_email__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = InvoiceStatus.choices
        ctx["selected_status"] = self.request.GET.get("status", "")
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = "erp/invoice_detail.html"
    context_object_name = "invoice"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["items"] = self.object.items.select_related("product").all()
        return ctx


class InvoiceCreateView(LoginRequiredMixin, View):
    """Create invoice along with line items via formset."""

    def get(self, request):
        form = InvoiceForm()
        formset = InvoiceItemFormSet()
        return render(request, "erp/invoice_form.html", {"form": form, "formset": formset})

    def post(self, request):
        form = InvoiceForm(request.POST)
        formset = InvoiceItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                invoice = form.save(commit=False)
                invoice.created_by = request.user
                invoice.save()

                formset.instance = invoice
                formset.save()

                invoice.recalculate_totals()

            messages.success(request, _("Invoice %(number)s created successfully.") % {"number": invoice.invoice_number})
            return redirect("erp:invoice_detail", pk=invoice.pk)

        return render(request, "erp/invoice_form.html", {"form": form, "formset": formset})


class InvoiceUpdateView(LoginRequiredMixin, View):
    """Edit invoice and line items."""

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        form = InvoiceForm(instance=invoice)
        formset = InvoiceItemFormSet(instance=invoice)
        return render(request, "erp/invoice_form.html", {"form": form, "formset": formset, "invoice": invoice})

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        form = InvoiceForm(request.POST, instance=invoice)
        formset = InvoiceItemFormSet(request.POST, instance=invoice)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                invoice = form.save()
                formset.save()
                invoice.recalculate_totals()

            messages.success(request, _("Invoice %(number)s updated successfully.") % {"number": invoice.invoice_number})
            return redirect("erp:invoice_detail", pk=invoice.pk)

        return render(request, "erp/invoice_form.html", {"form": form, "formset": formset, "invoice": invoice})


class InvoiceDeleteView(LoginRequiredMixin, DeleteView):
    model = Invoice
    template_name = "erp/confirm_delete.html"
    success_url = reverse_lazy("erp:invoice_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, _("Invoice deleted successfully."))
        return super().delete(request, *args, **kwargs)


class InvoiceStatusUpdateView(LoginRequiredMixin, View):
    """Quick transition of invoice status (e.g. mark as PAID, CANCELLED, SENT)."""

    def post(self, request, pk, new_status):
        invoice = get_object_or_404(Invoice, pk=pk)
        if new_status in InvoiceStatus.values:
            invoice.status = new_status
            invoice.save(update_fields=["status", "updated_at"])
            messages.success(
                request,
                _("Invoice %(number)s marked as %(status)s.")
                % {"number": invoice.invoice_number, "status": invoice.get_status_display()},
            )
        return redirect("erp:invoice_detail", pk=invoice.pk)


class InvoicePdfDownloadView(LoginRequiredMixin, View):
    """Generate and stream or download the PDF invoice."""

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        pdf_bytes = generate_invoice_pdf(invoice)

        filename = f"{invoice.invoice_number or 'invoice'}.pdf"
        disposition = "attachment" if request.GET.get("download") == "1" else "inline"

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        return response


class InvoiceSendEmailView(LoginRequiredMixin, View):
    """Send invoice PDF as email attachment to the customer."""

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        try:
            # Attempt Celery task execution, falling back to sync execution if broker unavailable
            try:
                send_invoice_email.delay(invoice.pk)
            except Exception as task_err:
                logger.info("Celery broker unavailable, executing send_invoice_email synchronously: %s", task_err)
                send_invoice_email(invoice.pk)

            messages.success(
                request,
                _("Invoice PDF email dispatched to %(email)s.") % {"email": invoice.customer_email},
            )
        except Exception as exc:
            logger.error("Failed sending invoice email: %s", exc)
            messages.error(request, _("Error delivering invoice email: %(err)s") % {"err": str(exc)})

        return redirect("erp:invoice_detail", pk=invoice.pk)

