from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


class HeroBlock(blocks.StructBlock):
    """Full-width hero banner block with optional CTA and background/side image."""

    heading = blocks.CharBlock(label=_("Heading"), max_length=160)
    subheading = blocks.TextBlock(label=_("Subheading"), required=False)
    cta_text = blocks.CharBlock(label=_("CTA Button Text"), required=False, max_length=60)
    cta_url = blocks.CharBlock(label=_("CTA URL"), required=False, max_length=255)
    image = ImageChooserBlock(label=_("Hero Image"), required=False)

    class Meta:
        icon = "image"
        label = _("Hero Banner")
        template = "cms/blocks/hero_block.html"


class RichTextSectionBlock(blocks.StructBlock):
    """Rich text editorial section with optional heading."""

    heading = blocks.CharBlock(label=_("Section Heading"), required=False, max_length=160)
    body = blocks.RichTextBlock(label=_("Body"))

    class Meta:
        icon = "doc-full"
        label = _("Rich Text Section")
        template = "cms/blocks/richtext_section_block.html"


class FeatureItemBlock(blocks.StructBlock):
    """Individual feature card within a FeatureGridBlock."""

    icon = blocks.CharBlock(
        label=_("FontAwesome 4.x Icon"),
        required=False,
        default="fa-star",
        max_length=50,
        help_text=_("FontAwesome 4.x icon class (e.g. fa-rocket, fa-shield)."),
    )
    title = blocks.CharBlock(label=_("Title"), max_length=120)
    description = blocks.TextBlock(label=_("Description"))

    class Meta:
        icon = "plus"
        label = _("Feature Item")


class FeatureGridBlock(blocks.StructBlock):
    """Responsive multi-column feature showcase grid."""

    heading = blocks.CharBlock(label=_("Grid Heading"), required=False, max_length=160)
    features = blocks.ListBlock(FeatureItemBlock(), label=_("Features"))

    class Meta:
        icon = "grip"
        label = _("Feature Grid")
        template = "cms/blocks/feature_grid_block.html"


class CallToActionBlock(blocks.StructBlock):
    """Prominent call-to-action banner linking to a conversion or contact route."""

    heading = blocks.CharBlock(label=_("Heading"), max_length=160)
    body = blocks.TextBlock(label=_("Supporting Text"), required=False)
    button_text = blocks.CharBlock(label=_("Button Text"), max_length=60)
    button_url = blocks.CharBlock(label=_("Button URL"), max_length=255)

    class Meta:
        icon = "pick"
        label = _("Call to Action")
        template = "cms/blocks/cta_block.html"


class CMSStreamBlock(blocks.StreamBlock):
    """Shared StreamField block palette for StandardPage and BlogPage."""

    hero = HeroBlock()
    richtext = RichTextSectionBlock()
    features = FeatureGridBlock()
    cta = CallToActionBlock()
