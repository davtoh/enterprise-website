from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views.generic import DetailView, ListView

from .models import VideoGallery, VideoItem


class GalleryListView(ListView):
    """
    Public gallery catalog view listing all active video galleries.
    """
    model = VideoGallery
    template_name = "video_gallery/gallery_list.html"
    context_object_name = "galleries"
    paginate_by = 9

    def get_queryset(self):
        queryset = (
            VideoGallery.objects.filter(is_active=True)
            .prefetch_related("videos")
            .order_by("-created_at")
        )
        search_query = self.request.GET.get("q", "").strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(videos__title__icontains=search_query)
            ).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "").strip()
        context["total_galleries"] = VideoGallery.objects.filter(is_active=True).count()
        context["total_videos"] = VideoItem.objects.filter(
            is_active=True, gallery__is_active=True
        ).count()
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
        return VideoGallery.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        gallery = self.object

        videos = gallery.active_videos()
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
        context["source_counts"] = gallery.get_source_counts()
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
        return VideoItem.objects.filter(is_active=True, gallery__is_active=True)
