from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .utils import (
    build_embed_url,
    build_thumbnail_url,
    detect_video_source,
    extract_vimeo_id,
    extract_youtube_id,
)

# Inline fallback SVG placeholder (16:9 ratio) when no thumbnail is available
DEFAULT_THUMBNAIL_SVG = (
    "data:image/svg+xml;charset=UTF-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20"
    "viewBox%3D%220%200%20640%20360%22%20width%3D%22100%25%22%20height%3D%22100%25%22%3E"
    "%3Cdefs%3E%3ClinearGradient%20id%3D%22g%22%20x1%3D%220%25%22%20y1%3D%220%25%22%20x2%3D%22100%25%22%20y2%3D%22100%25%22%3E"
    "%3Cstop%20offset%3D%220%25%22%20stop-color%3D%22%232b2d42%22%2F%3E"
    "%3Cstop%20offset%3D%22100%25%22%20stop-color%3D%22%231d1e2c%22%2F%3E%3C%2FlinearGradient%3E%3C%2Fdefs%3E"
    "%3Crect%20width%3D%22640%22%20height%3D%22360%22%20fill%3D%22url(%23g)%22%2F%3E"
    "%3Ccircle%20cx%3D%22320%22%20cy%3D%22180%22%20r%3D%2244%22%20fill%3D%22rgba(255%2C255%2C255%2C0.15)%22%2F%3E"
    "%3Cpolygon%20points%3D%22310%2C160%20340%2C180%20310%2C200%22%20fill%3D%22%23ffffff%22%2F%3E"
    "%3Ctext%20x%3D%22320%22%20y%3D%22255%22%20fill%3D%22%23a0aec0%22%20font-family%3D%22sans-serif%22%20font-size%3D%2216%22%20text-anchor%3D%22middle%22%3EVideo Preview%3C%2Ftext%3E"
    "%3C%2Fsvg%3E"
)


class VideoGallery(models.Model):
    """
    Categorized collection of video media items.
    """
    name = models.CharField(_("Name"), max_length=200)
    slug = models.SlugField(
        _("Slug"),
        max_length=200,
        unique=True,
        help_text=_("URL-friendly slug for public gallery routing (e.g. product-demos)"),
    )
    description = models.TextField(_("Description"), blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("Video Gallery")
        verbose_name_plural = _("Video Galleries")
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("video_gallery:gallery_detail", kwargs={"slug": self.slug})

    def active_videos(self):
        """Returns active videos ordered by display order then creation time."""
        return self.videos.filter(is_active=True).order_by("order", "created_at")

    @property
    def video_count(self) -> int:
        return self.active_videos().count()

    @property
    def cover_thumbnail_url(self) -> str:
        """Derives cover thumbnail from the first active video or returns the default SVG."""
        first_video = self.active_videos().first()
        if first_video:
            return first_video.display_thumbnail_url
        return DEFAULT_THUMBNAIL_SVG

    def get_source_counts(self) -> dict:
        """Returns a breakdown of video counts by source_type."""
        counts = {"all": 0, "youtube": 0, "vimeo": 0, "mp4": 0}
        for item in self.active_videos().values("source_type"):
            st = item["source_type"]
            counts["all"] += 1
            if st in counts:
                counts[st] += 1
        return counts


class VideoItem(models.Model):
    """
    Individual video item supporting YouTube, Vimeo embeds, or direct MP4 files.
    """
    SOURCE_YOUTUBE = "youtube"
    SOURCE_VIMEO = "vimeo"
    SOURCE_MP4 = "mp4"

    SOURCE_CHOICES = [
        (SOURCE_YOUTUBE, _("YouTube")),
        (SOURCE_VIMEO, _("Vimeo")),
        (SOURCE_MP4, _("MP4 Video")),
    ]

    gallery = models.ForeignKey(
        VideoGallery,
        on_delete=models.CASCADE,
        related_name="videos",
        verbose_name=_("Gallery"),
    )
    title = models.CharField(_("Title"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    source_type = models.CharField(
        _("Source Type"),
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_YOUTUBE,
    )
    embed_url = models.CharField(
        _("Embed URL or Share Link"),
        max_length=500,
        blank=True,
        help_text=_("YouTube or Vimeo watch/share link, or direct MP4 URL"),
    )
    video_file = models.FileField(
        _("Video File (MP4)"),
        upload_to="video_gallery/videos/",
        blank=True,
        null=True,
        help_text=_("Upload an MP4 file if not using an external link"),
    )
    thumbnail = models.ImageField(
        _("Custom Thumbnail"),
        upload_to="video_gallery/thumbnails/",
        blank=True,
        null=True,
        help_text=_("Optional custom thumbnail. Auto-derived for YouTube if left blank."),
    )
    order = models.PositiveIntegerField(_("Display Order"), default=0)
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("Video Item")
        verbose_name_plural = _("Video Items")
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_source_type_display()})"

    def clean(self):
        """Validates that a URL or uploaded video file is present and auto-detects source type."""
        super().clean()
        if not self.embed_url and not self.video_file:
            raise ValidationError(
                _("You must specify either an Embed URL / Share Link or upload a Video File.")
            )

        # Auto-detect source type from URL or file if not explicitly set to something else
        if self.video_file and not self.embed_url:
            self.source_type = self.SOURCE_MP4
        elif self.embed_url:
            detected = detect_video_source(self.embed_url, has_file=bool(self.video_file))
            if detected:
                self.source_type = detected

    def save(self, *args, **kwargs):
        """Auto-detects source_type on save if URL or file is provided."""
        if self.video_file and not self.embed_url:
            self.source_type = self.SOURCE_MP4
        elif self.embed_url:
            detected = detect_video_source(self.embed_url, has_file=bool(self.video_file))
            if detected:
                self.source_type = detected
        super().save(*args, **kwargs)

    @property
    def video_id(self) -> str:
        """Extracts provider video ID for YouTube or Vimeo."""
        if self.source_type == self.SOURCE_YOUTUBE:
            return extract_youtube_id(self.embed_url) or ""
        elif self.source_type == self.SOURCE_VIMEO:
            return extract_vimeo_id(self.embed_url) or ""
        return ""

    @property
    def embed_player_url(self) -> str:
        """Returns standard iframe embed URL."""
        return build_embed_url(
            self.source_type,
            self.embed_url,
            video_id=self.video_id,
            autoplay=False,
        )

    @property
    def autoplay_embed_url(self) -> str:
        """Returns iframe embed URL with autoplay enabled for modal playback."""
        return build_embed_url(
            self.source_type,
            self.embed_url,
            video_id=self.video_id,
            autoplay=True,
        )

    @property
    def display_thumbnail_url(self) -> str:
        """Returns custom thumbnail, auto-derived provider thumbnail, or default SVG."""
        if self.thumbnail:
            try:
                return self.thumbnail.url
            except Exception:
                pass

        derived = build_thumbnail_url(self.source_type, self.embed_url, self.video_id)
        if derived:
            return derived

        return DEFAULT_THUMBNAIL_SVG

    @property
    def direct_media_url(self) -> str:
        """Returns direct video file URL for HTML5 player."""
        if self.video_file:
            try:
                return self.video_file.url
            except Exception:
                pass
        if self.source_type == self.SOURCE_MP4 and self.embed_url:
            return self.embed_url
        return ""

    @property
    def is_direct_html5(self) -> bool:
        """Returns True if the video should be rendered using HTML5 <video> tag."""
        return self.source_type == self.SOURCE_MP4 or bool(self.video_file)
