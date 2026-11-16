from import_export import resources
from .models import Invoice, Product, StockMovement


class ProductResource(resources.ModelResource):
    """Import/export resource for ERP Product catalog records."""

    class Meta:
        model = Product
        import_id_fields = ("id",)
        fields = (
            "id",
            "sku",
            "name",
            "slug",
            "category",
            "unit",
            "unit_price",
            "cost_price",
            "current_stock",
            "reorder_threshold",
            "is_active",
            "is_published",
            "created_at",
        )
        export_order = fields


class InvoiceResource(resources.ModelResource):
    """Import/export resource for ERP Invoice records."""

    class Meta:
        model = Invoice
        import_id_fields = ("id",)
        fields = (
            "id",
            "invoice_number",
            "crm_company",
            "crm_contact",
            "customer_name",
            "customer_email",
            "issue_date",
            "due_date",
            "status",
            "subtotal",
            "tax_rate",
            "tax_amount",
            "discount_amount",
            "total_amount",
            "created_at",
        )
        export_order = fields


class StockMovementResource(resources.ModelResource):
    """Import/export resource for ERP StockMovement audit records."""

    class Meta:
        model = StockMovement
        import_id_fields = ("id",)
        fields = (
            "id",
            "product",
            "location",
            "movement_type",
            "quantity",
            "reference",
            "notes",
            "created_by",
            "created_at",
        )
        export_order = fields
