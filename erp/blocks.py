from django.utils.translation import gettext_lazy as _
from wagtail import blocks


class ProductShowcaseBlock(blocks.StructBlock):
    """Composable Wagtail block displaying published ERP products."""

    heading = blocks.CharBlock(label=_("Heading"), required=False, max_length=160)
    category_slug = blocks.CharBlock(
        label=_("Category Slug"),
        required=False,
        max_length=140,
        help_text=_("Optional ERP category slug to filter displayed products."),
    )
    max_items = blocks.IntegerBlock(
        label=_("Max Products"),
        default=6,
        min_value=1,
        max_value=24,
        required=False,
    )
    show_prices = blocks.BooleanBlock(
        label=_("Show Unit Prices"),
        default=True,
        required=False,
    )

    class Meta:
        icon = "tag"
        label = _("ERP Product Showcase")
        template = "cms/blocks/product_showcase_block.html"

    def get_context(self, value, parent_context=None):
        """Resolve only active, published ERP products."""
        from erp.models import Product

        context = super().get_context(value, parent_context=parent_context)
        category_slug = (value.get("category_slug") or "").strip()
        max_items = value.get("max_items") or 6

        qs = (
            Product.objects.filter(is_active=True, is_published=True)
            .select_related("category")
            .order_by("name")
        )
        if category_slug:
            qs = qs.filter(category__slug=category_slug)

        context["products"] = list(qs[:max_items])
        context["show_prices"] = bool(value.get("show_prices", True))
        return context
