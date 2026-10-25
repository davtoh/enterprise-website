from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import (
    Category,
    InventoryLocation,
    Product,
    StockMovement,
    Invoice,
    InvoiceItem,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "product_count", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = _("Products")


@admin.register(InventoryLocation)
class InventoryLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code", "address")


class StockMovementInline(admin.TabularInline):
    model = StockMovement
    extra = 0
    fields = ("movement_type", "quantity", "location", "reference", "created_at")
    readonly_fields = ("created_at",)
    can_delete = False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sku",
        "category",
        "unit_price",
        "cost_price",
        "current_stock",
        "reorder_threshold",
        "stock_status",
        "is_active",
    )
    list_filter = ("category", "is_active")
    search_fields = ("name", "sku", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [StockMovementInline]

    def stock_status(self, obj):
        if obj.current_stock <= 0:
            return format_html('<span style="color:red; font-weight:bold;">{}</span>', _("Out of Stock"))
        elif obj.current_stock <= obj.reorder_threshold:
            return format_html('<span style="color:orange; font-weight:bold;">{}</span>', _("Low Stock"))
        return format_html('<span style="color:green;">{}</span>', _("In Stock"))
    stock_status.short_description = _("Stock Status")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "movement_type",
        "product",
        "quantity",
        "location",
        "reference",
        "created_by",
    )
    list_filter = ("movement_type", "location", "created_at")
    search_fields = ("product__name", "product__sku", "reference", "notes")
    date_hierarchy = "created_at"


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ("product", "description", "quantity", "unit_price", "total_price")
    readonly_fields = ("total_price",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "customer_name",
        "issue_date",
        "due_date",
        "status_badge",
        "total_amount",
        "created_by",
    )
    list_filter = ("status", "issue_date", "due_date")
    search_fields = ("invoice_number", "customer_name", "customer_email")
    inlines = [InvoiceItemInline]
    readonly_fields = ("subtotal", "tax_amount", "total_amount", "created_at", "updated_at")

    def status_badge(self, obj):
        badge_colors = {
            "DRAFT": "#64748b",
            "SENT": "#2563eb",
            "PAID": "#16a34a",
            "OVERDUE": "#dc2626",
            "CANCELLED": "#475569",
        }
        color = badge_colors.get(obj.status, "#64748b")
        return format_html(
            '<span style="background-color:{}; color:white; padding:3px 8px; border-radius:4px; font-size:11px;">{}</span>',
            color,
            obj.get_status_display(),
        )
    status_badge.short_description = _("Status")
