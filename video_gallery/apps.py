from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class VideoGalleryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'video_gallery'
    verbose_name = _('Video Gallery')
