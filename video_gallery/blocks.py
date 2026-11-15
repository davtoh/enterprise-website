from django.utils.translation import gettext_lazy as _
from wagtail import blocks


class VideoGalleryEmbedBlock(blocks.StructBlock):
    """Composable Wagtail block for embedding a public VideoGallery."""

    heading = blocks.CharBlock(label=_("Heading"), required=False, max_length=160)
    gallery_slug = blocks.CharBlock(
        label=_("Gallery Slug"),
        max_length=200,
        help_text=_("Slug of the public VideoGallery to embed."),
    )
    max_items = blocks.IntegerBlock(
        label=_("Max Videos"),
        default=6,
        min_value=1,
        max_value=24,
        required=False,
    )

    class Meta:
        icon = "media"
        label = _("Video Gallery Embed")
        template = "cms/blocks/video_gallery_embed_block.html"

    def get_context(self, value, parent_context=None):
        """Resolve only active, public, non-staff galleries and videos."""
        from .models import VideoGallery

        context = super().get_context(value, parent_context=parent_context)
        slug = (value.get("gallery_slug") or "").strip()
        max_items = value.get("max_items") or 6

        gallery = (
            VideoGallery.objects.filter(
                slug=slug,
                is_active=True,
                is_public=True,
                requires_staff=False,
            ).first()
            if slug
            else None
        )
        videos = list(gallery.public_videos()[:max_items]) if gallery else []
        context["gallery"] = gallery
        context["videos"] = videos
        return context
