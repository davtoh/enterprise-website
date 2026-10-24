import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from plugin_registry import registry
from video_gallery.models import VideoGallery, VideoItem
from video_gallery.utils import (
    build_embed_url,
    build_thumbnail_url,
    detect_video_source,
    extract_vimeo_id,
    extract_youtube_id,
)


# =====================================================================
# Unit Tests: URL Parser & Embed Utilities
# =====================================================================

class TestVideoGalleryUtils:
    """Tests for URL extraction, auto-detection, and embed construction."""

    @pytest.mark.parametrize(
        "url,expected_id",
        [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtube.com/watch?v=dQw4w9WgXcQ&t=45s", "dQw4w9WgXcQ"),
            ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ?t=10", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/v/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("", None),
            ("https://example.com/not-youtube", None),
        ],
    )
    def test_extract_youtube_id(self, url, expected_id):
        assert extract_youtube_id(url) == expected_id

    @pytest.mark.parametrize(
        "url,expected_id",
        [
            ("https://vimeo.com/76979871", "76979871"),
            ("https://www.vimeo.com/76979871", "76979871"),
            ("https://player.vimeo.com/video/76979871", "76979871"),
            ("https://vimeo.com/channels/staffpicks/76979871", "76979871"),
            ("https://vimeo.com/groups/motion/videos/76979871", "76979871"),
            ("https://vimeo.com/manage/videos/76979871", "76979871"),
            ("76979871", "76979871"),
            ("", None),
            ("https://example.com/not-vimeo", None),
        ],
    )
    def test_extract_vimeo_id(self, url, expected_id):
        assert extract_vimeo_id(url) == expected_id

    def test_detect_video_source(self):
        assert detect_video_source("https://www.youtube.com/watch?v=abc") == "youtube"
        assert detect_video_source("https://youtu.be/abc") == "youtube"
        assert detect_video_source("https://vimeo.com/123456") == "vimeo"
        assert detect_video_source("https://example.com/media/clip.mp4") == "mp4"
        assert detect_video_source("https://example.com/video/presentation") == "mp4"
        assert detect_video_source(has_file=True) == "mp4"

    def test_build_embed_url(self):
        # YouTube default
        yt_url = build_embed_url("youtube", "https://youtu.be/dQw4w9WgXcQ", autoplay=False)
        assert "youtube-nocookie.com/embed/dQw4w9WgXcQ" in yt_url
        assert "rel=0" in yt_url
        assert "autoplay=1" not in yt_url

        # YouTube autoplay
        yt_auto = build_embed_url("youtube", "https://youtu.be/dQw4w9WgXcQ", autoplay=True)
        assert "autoplay=1" in yt_auto

        # Vimeo default
        vm_url = build_embed_url("vimeo", "https://vimeo.com/76979871", autoplay=False)
        assert "player.vimeo.com/video/76979871" in vm_url
        assert "dnt=1" in vm_url
        assert "autoplay=1" not in vm_url

        # Vimeo autoplay
        vm_auto = build_embed_url("vimeo", "https://vimeo.com/76979871", autoplay=True)
        assert "autoplay=1" in vm_auto

        # MP4 direct
        mp4_url = build_embed_url("mp4", "https://cdn.example.com/demo.mp4")
        assert mp4_url == "https://cdn.example.com/demo.mp4"

    def test_build_thumbnail_url(self):
        yt_thumb = build_thumbnail_url("youtube", "https://youtu.be/dQw4w9WgXcQ")
        assert yt_thumb == "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg"

        vm_thumb = build_thumbnail_url("vimeo", "https://vimeo.com/76979871")
        assert vm_thumb is None


# =====================================================================
# Model Tests
# =====================================================================

@pytest.mark.django_db
class TestVideoGalleryModels:
    """Tests for VideoGallery and VideoItem models."""

    def test_create_gallery(self):
        gallery = VideoGallery.objects.create(
            name="Product Demos",
            slug="product-demos",
            description="Enterprise showcase videos",
        )
        assert str(gallery) == "Product Demos"
        assert gallery.get_absolute_url() == reverse("video_gallery:gallery_detail", kwargs={"slug": "product-demos"})
        assert gallery.video_count == 0
        assert "data:image/svg+xml" in gallery.cover_thumbnail_url

    def test_video_item_validation_empty_error(self):
        gallery = VideoGallery.objects.create(name="Empty Gallery", slug="empty-gallery")
        item = VideoItem(gallery=gallery, title="Missing Source")
        with pytest.raises(ValidationError):
            item.clean()

    def test_create_youtube_video_item(self):
        gallery = VideoGallery.objects.create(name="Tech Tutorials", slug="tech-tutorials")
        item = VideoItem.objects.create(
            gallery=gallery,
            title="Getting Started with Antigravity",
            embed_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
        assert item.source_type == VideoItem.SOURCE_YOUTUBE
        assert item.video_id == "dQw4w9WgXcQ"
        assert "img.youtube.com/vi/dQw4w9WgXcQ" in item.display_thumbnail_url
        assert "youtube-nocookie.com/embed/dQw4w9WgXcQ" in item.embed_player_url
        assert "autoplay=1" in item.autoplay_embed_url
        assert not item.is_direct_html5
        assert str(item) == "Getting Started with Antigravity (YouTube)"

    def test_create_vimeo_video_item(self):
        gallery = VideoGallery.objects.create(name="Creative Showreels", slug="showreels")
        item = VideoItem.objects.create(
            gallery=gallery,
            title="Design Principles 2026",
            embed_url="https://vimeo.com/76979871",
        )
        assert item.source_type == VideoItem.SOURCE_VIMEO
        assert item.video_id == "76979871"
        assert "player.vimeo.com/video/76979871" in item.embed_player_url
        assert not item.is_direct_html5

    def test_create_mp4_video_item_with_file(self):
        gallery = VideoGallery.objects.create(name="Internal Training", slug="internal-training")
        fake_video = SimpleUploadedFile("sample.mp4", b"dummy video bytes", content_type="video/mp4")
        item = VideoItem.objects.create(
            gallery=gallery,
            title="Security Onboarding",
            video_file=fake_video,
        )
        item.clean()
        assert item.source_type == VideoItem.SOURCE_MP4
        assert item.is_direct_html5 is True
        assert item.direct_media_url != ""

    def test_gallery_source_counts_and_active_filtering(self):
        gallery = VideoGallery.objects.create(name="Mixed Media", slug="mixed-media")
        VideoItem.objects.create(
            gallery=gallery,
            title="YT 1",
            embed_url="https://youtu.be/dQw4w9WgXcQ",
            is_active=True,
        )
        VideoItem.objects.create(
            gallery=gallery,
            title="Vimeo 1",
            embed_url="https://vimeo.com/76979871",
            is_active=True,
        )
        VideoItem.objects.create(
            gallery=gallery,
            title="MP4 1",
            embed_url="https://example.com/test.mp4",
            is_active=True,
        )
        VideoItem.objects.create(
            gallery=gallery,
            title="Inactive YT",
            embed_url="https://youtu.be/dQw4w9WgXcQ",
            is_active=False,
        )

        assert gallery.video_count == 3
        counts = gallery.get_source_counts()
        assert counts["all"] == 3
        assert counts["youtube"] == 1
        assert counts["vimeo"] == 1
        assert counts["mp4"] == 1


# =====================================================================
# View & Route Tests
# =====================================================================

@pytest.mark.django_db
class TestVideoGalleryViews:
    """Tests for public views and URLs."""

    @pytest.fixture
    def sample_gallery(self):
        gallery = VideoGallery.objects.create(
            name="Architecture & Engineering",
            slug="architecture-engineering",
            description="Technical architecture walkthroughs and guides.",
            is_active=True,
        )
        VideoItem.objects.create(
            gallery=gallery,
            title="Django Modernization Overview",
            description="Deep dive into Python 3.12 and Django 5.",
            embed_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            is_active=True,
            order=1,
        )
        VideoItem.objects.create(
            gallery=gallery,
            title="Vimeo Showcase Demo",
            description="Interactive presentation.",
            embed_url="https://vimeo.com/76979871",
            is_active=True,
            order=2,
        )
        return gallery

    def test_gallery_list_view(self, client, sample_gallery):
        response = client.get(reverse("video_gallery:gallery_list"))
        assert response.status_code == 200
        content = response.content.decode()
        assert "Media &amp; Video Galleries" in content or "Media & Video Galleries" in content
        assert "Architecture &amp; Engineering" in content or "Architecture & Engineering" in content

    def test_gallery_list_search(self, client, sample_gallery):
        response = client.get(reverse("video_gallery:gallery_list") + "?q=Architecture")
        assert response.status_code == 200
        assert "Architecture &amp; Engineering" in response.content.decode() or "Architecture & Engineering" in response.content.decode()

        # Non-matching search
        response_empty = client.get(reverse("video_gallery:gallery_list") + "?q=NonExistentKeywordXYZ")
        assert response_empty.status_code == 200
        assert "No Video Galleries Found" in response_empty.content.decode()

    def test_gallery_detail_view(self, client, sample_gallery):
        response = client.get(sample_gallery.get_absolute_url())
        assert response.status_code == 200
        content = response.content.decode()
        assert "Architecture &amp; Engineering" in content or "Architecture & Engineering" in content
        assert "Django Modernization Overview" in content
        assert "Vimeo Showcase Demo" in content

    def test_gallery_detail_filter_by_source(self, client, sample_gallery):
        # Filter for YouTube
        res_yt = client.get(sample_gallery.get_absolute_url() + "?source=youtube")
        assert res_yt.status_code == 200
        content_yt = res_yt.content.decode()
        assert "Django Modernization Overview" in content_yt
        assert "Vimeo Showcase Demo" not in content_yt

        # Filter for Vimeo
        res_vm = client.get(sample_gallery.get_absolute_url() + "?source=vimeo")
        assert res_vm.status_code == 200
        content_vm = res_vm.content.decode()
        assert "Vimeo Showcase Demo" in content_vm
        assert "Django Modernization Overview" not in content_vm

    def test_gallery_detail_404_on_inactive(self, client):
        inactive = VideoGallery.objects.create(name="Draft", slug="draft-gallery", is_active=False)
        response = client.get(reverse("video_gallery:gallery_detail", kwargs={"slug": inactive.slug}))
        assert response.status_code == 404

    def test_gallery_detail_404_on_nonexistent(self, client):
        response = client.get(reverse("video_gallery:gallery_detail", kwargs={"slug": "missing-slug-xyz"}))
        assert response.status_code == 404

    def test_video_modal_view(self, client, sample_gallery):
        video = sample_gallery.videos.first()
        url = reverse("video_gallery:video_modal", kwargs={"pk": video.pk})
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        assert video.title in content
        assert "youtube-nocookie.com/embed" in content

    def test_videos_alias_redirect(self, client):
        response = client.get("/videos/")
        assert response.status_code == 302
        assert response.url == "/media/"


# =====================================================================
# Plugin & Admin Integration Tests
# =====================================================================

@pytest.mark.django_db
class TestVideoGalleryPluginAndAdmin:
    """Tests for AppPlugin and Django Admin registration."""

    def test_plugin_registered(self):
        plugin_cls = registry.get_plugin("video_gallery")
        assert plugin_cls is not None
        assert plugin_cls.name == "video_gallery"
        assert plugin_cls.icon == "fa fa-video-camera"
        
        menu_items = plugin_cls.get_menu_items()
        assert len(menu_items) == 1
        assert menu_items[0].label == "Media Gallery"
        assert menu_items[0].url_name == "video_gallery:gallery_list"

    def test_admin_previews(self, admin_client):
        gallery = VideoGallery.objects.create(name="Admin Gallery", slug="admin-gallery")
        video = VideoItem.objects.create(
            gallery=gallery,
            title="Admin Video Test",
            embed_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )

        # Admin changelist for galleries
        res_gallery_list = admin_client.get(reverse("admin:video_gallery_videogallery_changelist"))
        assert res_gallery_list.status_code == 200
        assert "Admin Gallery" in res_gallery_list.content.decode()

        # Admin changelist for videos
        res_video_list = admin_client.get(reverse("admin:video_gallery_videoitem_changelist"))
        assert res_video_list.status_code == 200
        assert "Admin Video Test" in res_video_list.content.decode()
        assert "img.youtube.com" in res_video_list.content.decode()

        # Admin changeform for video
        res_video_change = admin_client.get(reverse("admin:video_gallery_videoitem_change", args=[video.pk]))
        assert res_video_change.status_code == 200
        assert "Live Player Preview" in res_video_change.content.decode()
