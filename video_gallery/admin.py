from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .models import VideoGallery, VideoItem


class VideoItemInline(admin.TabularInline):
    model = VideoItem
    extra = 1
    fields = (
        "thumbnail_preview",
        "title",
        "source_type",
        "embed_url",
        "video_file",
        "order",
        "is_active",
    )
    readonly_fields = ("thumbnail_preview",)

    def thumbnail_preview(self, obj):
        if not obj or not obj.pk:
            return mark_safe('<span class="text-muted">—</span>')
        thumb_url = obj.display_thumbnail_url
        return format_html(
            '<img src="{}" alt="{}" style="width: 72px; height: 40px; object-fit: cover; border-radius: 4px;" />',
            thumb_url,
            obj.title,
        )
    thumbnail_preview.short_description = _("Thumbnail")


@admin.register(VideoGallery)
class VideoGalleryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "get_video_count", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [VideoItemInline]

    def get_video_count(self, obj):
        count = obj.videos.count()
        return format_html(
            '<span class="badge bg-secondary" style="font-weight: 600;">{}</span>',
            count,
        )
    get_video_count.short_description = _("Videos")


@admin.register(VideoItem)
class VideoItemAdmin(admin.ModelAdmin):
    list_display = (
        "thumbnail_preview",
        "title",
        "gallery",
        "source_type",
        "order",
        "is_active",
        "created_at",
    )
    list_filter = ("gallery", "source_type", "is_active", "created_at")
    search_fields = ("title", "description", "embed_url")
    readonly_fields = (
        "thumbnail_preview_large",
        "embed_player_preview",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            _("Video Information"),
            {"fields": ("gallery", "title", "description", "source_type")},
        ),
        (
            _("Media Source"),
            {
                "fields": (
                    "embed_url",
                    "video_file",
                    "thumbnail",
                ),
                "description": _(
                    "Paste a YouTube or Vimeo share link, or upload an MP4 file. "
                    "For YouTube, thumbnails are derived automatically if left blank."
                ),
            },
        ),
        (
            _("Media Previews"),
            {
                "fields": ("thumbnail_preview_large", "embed_player_preview"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Display & Publishing"),
            {"fields": ("order", "is_active", "created_at", "updated_at")},
        ),
    )

    def thumbnail_preview(self, obj):
        if not obj or not obj.pk:
            return mark_safe('<span class="text-muted">—</span>')
        thumb_url = obj.display_thumbnail_url
        return format_html(
            '<img src="{}" alt="{}" style="width: 80px; height: 45px; object-fit: cover; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.2);" />',
            thumb_url,
            obj.title,
        )
    thumbnail_preview.short_description = _("Thumb")

    def thumbnail_preview_large(self, obj):
        if not obj or not obj.pk:
            return _("Save item first to generate preview.")
        thumb_url = obj.display_thumbnail_url
        return format_html(
            '<div style="max-width: 320px;">'
            '<img src="{}" alt="{}" style="width: 100%; border-radius: 6px; box-shadow: 0 2px 6px rgba(0,0,0,0.15);" />'
            '</div>',
            thumb_url,
            obj.title,
        )
    thumbnail_preview_large.short_description = _("Thumbnail Preview")

    def embed_player_preview(self, obj):
        if not obj or not obj.pk:
            return _("Save item first to view embed player.")
        
        if obj.is_direct_html5 and obj.direct_media_url:
            return format_html(
                '<div style="max-width: 480px; aspect-ratio: 16/9;">'
                '<video src="{}" controls style="width: 100%; height: 100%; border-radius: 6px; background: #000;"></video>'
                '</div>',
                obj.direct_media_url,
            )
        elif obj.embed_player_url:
            return format_html(
                '<div style="max-width: 480px; aspect-ratio: 16/9;">'
                '<iframe src="{}" frameborder="0" allowfullscreen '
                'style="width: 100%; height: 100%; border-radius: 6px;" '
                'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"></iframe>'
                '</div>',
                obj.embed_player_url,
            )
        return mark_safe('<span class="text-muted">No media URL or file available</span>')
    embed_player_preview.short_description = _("Live Player Preview")
