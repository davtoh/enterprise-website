from decimal import Decimal
from django.conf import settings
from django.db import models, transaction
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """Product catalog category grouping."""

    name = models.CharField(max_length=120, unique=True, verbose_name=_("Category Name"))
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True, verbose_name=_("Description"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class InventoryLocation(models.Model):
    """Physical or logical stock storage location (warehouse, storefront, assembly)."""

    name = models.CharField(max_length=150, verbose_name=_("Location Name"))
    code = models.CharField(max_length=50, unique=True, verbose_name=_("Location Code"))
    address = models.TextField(blank=True, verbose_name=_("Address / Bin Location"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Inventory Location")
        verbose_name_plural = _("Inventory Locations")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Product(models.Model):
    """Core inventory product item."""

    sku = models.CharField(max_length=64, unique=True, verbose_name=_("SKU / Item Code"))
    name = models.CharField(max_length=200, verbose_name=_("Product Name"))
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name=_("Category"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))
    public_summary = models.CharField(
        max_length=300,
        blank=True,
        verbose_name=_("Public Summary"),
    )
    unit = models.CharField(max_length=30, default="pcs", verbose_name=_("Unit of Measure"))
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Selling Unit Price"),
    )
    cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Cost Price"),
    )
    current_stock = models.IntegerField(default=0, verbose_name=_("Current Stock"))
    reorder_threshold = models.IntegerField(default=10, verbose_name=_("Reorder Threshold"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    is_published = models.BooleanField(
        default=True,
        verbose_name=_("Published to Public Catalog"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "product"
            candidate = base_slug
            idx = 1
            while Product.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base_slug}-{idx}"
                idx += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    @property
    def is_low_stock(self) -> bool:
        return self.current_stock <= self.reorder_threshold

    @property
    def stock_value(self) -> Decimal:
        return Decimal(self.current_stock) * self.unit_price

    @property
    def cost_value(self) -> Decimal:
        return Decimal(self.current_stock) * self.cost_price

    @property
    def margin(self) -> Decimal:
        return self.unit_price - self.cost_price


class StockMovementType(models.TextChoices):
    IN = "IN", _("Stock In / Received")
    OUT = "OUT", _("Stock Out / Sold")
    ADJUSTMENT = "ADJUSTMENT", _("Adjustment / Audit")
    RETURN = "RETURN", _("Customer Return")


class StockMovement(models.Model):
    """Audit log of stock movements altering on-hand inventory levels."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stock_movements",
        verbose_name=_("Product"),
    )
    location = models.ForeignKey(
        InventoryLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
        verbose_name=_("Location"),
    )
    movement_type = models.CharField(
        max_length=20,
        choices=StockMovementType.choices,
        default=StockMovementType.IN,
        verbose_name=_("Movement Type"),
    )
    quantity = models.IntegerField(verbose_name=_("Quantity"))
    reference = models.CharField(max_length=120, blank=True, verbose_name=_("Reference / Document #"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Created By"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Stock Movement")
        verbose_name_plural = _("Stock Movements")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.movement_type} {self.quantity} {self.product.sku} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

        if is_new:
            # Atomically update current stock on product
            with transaction.atomic():
                product = Product.objects.select_for_update().get(pk=self.product_id)
                qty = self.quantity
                if self.movement_type in (StockMovementType.IN, StockMovementType.RETURN):
                    product.current_stock += abs(qty)
                elif self.movement_type == StockMovementType.OUT:
                    product.current_stock -= abs(qty)
                elif self.movement_type == StockMovementType.ADJUSTMENT:
                    product.current_stock += qty

                product.save(update_fields=["current_stock", "updated_at"])
