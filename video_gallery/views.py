from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views.generic import DetailView, ListView

from .models import VideoGallery, VideoItem


def _is_staff_user(request) -> bool:
    """Return True when the request user is an authenticated staff member."""
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated and user.is_staff)


class GalleryListView(ListView):
    """
    Public gallery catalog view listing all active video galleries.
    """
    model = VideoGallery
    template_name = "video_gallery/gallery_list.html"
    context_object_name = "galleries"
    paginate_by = 9

    def get_queryset(self):
        is_staff = _is_staff_user(self.request)
        queryset = (
            VideoGallery.objects.filter(is_active=True)
            .prefetch_related("videos")
            .order_by("-created_at")
        )
        if not is_staff:
            queryset = queryset.filter(is_public=True, requires_staff=False)
        search_query = self.request.GET.get("q", "").strip()
        if search_query:
            video_filter = Q(videos__title__icontains=search_query)
            if not is_staff:
                video_filter &= Q(
                    videos__is_public=True,
                    videos__requires_staff=False,
                    videos__security_events__isnull=True,
                )
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
                | video_filter
            ).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        is_staff = _is_staff_user(self.request)
        galleries_qs = VideoGallery.objects.filter(is_active=True)
        videos_qs = VideoItem.objects.filter(is_active=True, gallery__is_active=True)
        if not is_staff:
            galleries_qs = galleries_qs.filter(is_public=True, requires_staff=False)
            videos_qs = videos_qs.filter(
                is_public=True,
                requires_staff=False,
                gallery__is_public=True,
                gallery__requires_staff=False,
                security_events__isnull=True,
            )
        context["search_query"] = self.request.GET.get("q", "").strip()
        context["total_galleries"] = galleries_qs.count()
        context["total_videos"] = videos_qs.count()
        return context


class GalleryDetailView(DetailView):
    """
    Public gallery detail view displaying all active videos in a responsive grid
    with source filtering (YouTube, Vimeo, MP4 direct) and search.
    """
    model = VideoGallery
    template_name = "video_gallery/gallery_detail.html"
    context_object_name = "gallery"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        queryset = VideoGallery.objects.filter(is_active=True)
        if not _is_staff_user(self.request):
            queryset = queryset.filter(is_public=True, requires_staff=False)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        gallery = self.object
        is_staff = _is_staff_user(self.request)

        videos = gallery.active_videos() if is_staff else gallery.public_videos()
        source_filter = self.request.GET.get("source", "all").strip().lower()
        if source_filter in ["youtube", "vimeo", "mp4"]:
            videos = videos.filter(source_type=source_filter)

        search_query = self.request.GET.get("q", "").strip()
        if search_query:
            videos = videos.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
            )

        context["videos"] = videos
        context["active_source"] = source_filter
        context["search_query"] = search_query
        context["source_counts"] = gallery.get_source_counts(include_staff=is_staff)
        return context


class VideoItemModalView(DetailView):
    """
    Partial view rendering an interactive embed/HTML5 player modal snippet
    for HTMX or dynamic modal requests.
    """
    model = VideoItem
    template_name = "video_gallery/partials/player_modal_content.html"
    context_object_name = "video"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        queryset = VideoItem.objects.filter(is_active=True, gallery__is_active=True)
        if not _is_staff_user(self.request):
            queryset = queryset.filter(
                is_public=True,
                requires_staff=False,
                gallery__is_public=True,
                gallery__requires_staff=False,
                security_events__isnull=True,
            )
        return queryset
