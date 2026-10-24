from django.utils.translation import gettext_lazy as _
from plugin_registry import AppPlugin, MenuItemDefinition


class VideoGalleryPlugin(AppPlugin):
    name = "video_gallery"
    verbose_name = _("Media Gallery")
    description = _("Admin-managed embed-based video galleries supporting YouTube, Vimeo, and MP4")
    icon = "fa fa-video-camera"
    category = "productivity"

    menu_items = [
        MenuItemDefinition(
            label=_("Media Gallery"),
            url_name="video_gallery:gallery_list",
            icon="fa fa-video-camera",
            order=35,
            parent_slug="Apps",
        )
    ]
