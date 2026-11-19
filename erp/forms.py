from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _
from .models import (
    Product,
    Category,
    InventoryLocation,
    StockMovement,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    StockMovementType,
)


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "sku",
            "name",
            "category",
            "description",
            "public_summary",
            "unit",
            "unit_price",
            "cost_price",
            "current_stock",
            "reorder_threshold",
            "is_active",
            "is_published",
        ]
        widgets = {
            "sku": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. PRD-001"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Product name"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "public_summary": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Short marketing summary for public catalog"}
            ),
            "unit": forms.TextInput(attrs={"class": "form-control", "placeholder": "pcs, kg, box"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "cost_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "current_stock": forms.NumberInput(attrs={"class": "form-control"}),
            "reorder_threshold": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_published": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Category title"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class InventoryLocationForm(forms.ModelForm):
    class Meta:
        model = InventoryLocation
        fields = ["name", "code", "address", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Main Warehouse"}),
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "WH-MAIN"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ["product", "location", "movement_type", "quantity", "reference", "notes"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "location": forms.Select(attrs={"class": "form-select"}),
            "movement_type": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "reference": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. PO-8901, INV-2026-001"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean_quantity(self):
        qty = self.cleaned_data.get("quantity")
        if qty is None or qty == 0:
            raise forms.ValidationError(_("Quantity must be a non-zero integer."))
        return qty


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            "crm_company",
            "crm_contact",
            "customer_name",
            "customer_email",
            "customer_address",
            "issue_date",
            "due_date",
            "status",
            "tax_rate",
            "discount_amount",
            "notes",
        ]
        widgets = {
            "crm_company": forms.Select(attrs={"class": "form-select"}),
            "crm_contact": forms.Select(attrs={"class": "form-select"}),
            "customer_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Customer or Company name"}),
            "customer_email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "client@example.com"}),
            "customer_address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "issue_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "due_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "tax_rate": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "discount_amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Payment terms and banking instructions"}),
        }

    def clean(self):
        cleaned = super().clean()
        name = (cleaned.get("customer_name") or "").strip()
        if not name and not cleaned.get("crm_company") and not cleaned.get("crm_contact"):
            self.add_error(
                "customer_name",
                _("Provide a customer name or select a linked CRM company/contact."),
            )
        return cleaned


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ["product", "description", "quantity", "unit_price"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "description": forms.TextInput(attrs={"class": "form-control", "placeholder": "Item description"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }


InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=1,
    can_delete=True,
)
