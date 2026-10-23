import io
import pytest
from PIL import Image
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory

from user_management.forms import SiteUserCreationForm, years_ago
from utils import get_referer_view


def create_test_image(size=(50, 50), color="blue", format="JPEG"):
    """Helper to generate in-memory dummy image file for upload testing."""
    file_obj = io.BytesIO()
    image = Image.new("RGB", size=size, color=color)
    image.save(file_obj, format=format)
    file_obj.seek(0)
    return SimpleUploadedFile(
        f"test.{format.lower()}",
        file_obj.read(),
        content_type=f"image/{format.lower()}",
    )


def test_get_referer_view_empty(rf):
    request = rf.get("/")
    assert get_referer_view(request, default="/default/") == "/default/"


def test_get_referer_view_different_host(rf):
    request = rf.get("/", HTTP_REFERER="https://malicious.com/phishing/", SERVER_NAME="testserver")
    assert get_referer_view(request, default="/default/") == "/default/"


def test_get_referer_view_valid_same_host(rf):
    request = rf.get(
        "/",
        HTTP_REFERER="http://testserver/dashboard/overview/",
        SERVER_NAME="testserver",
    )
    assert get_referer_view(request) == "/dashboard/overview/"


def test_years_ago_calculation():
    import datetime
    today = datetime.date(2026, 10, 22)
    ten_years_ago = years_ago(10, from_date=today)
    assert ten_years_ago == datetime.date(2016, 10, 22)


@pytest.mark.django_db
class TestFormAvatarValidation:
    """Tests for SiteUserCommonForm avatar validation logic."""

    def test_clean_profile_picture_none(self):
        form = SiteUserCreationForm()
        form.cleaned_data = {"profile_picture": None}
        assert form.clean_profile_picture() is None

    def test_clean_profile_picture_valid(self):
        form = SiteUserCreationForm()
        valid_img = create_test_image(size=(80, 80))
        form.cleaned_data = {"profile_picture": valid_img}
        assert form.clean_profile_picture() == valid_img

    def test_clean_profile_picture_oversized_dimensions(self):
        form = SiteUserCreationForm()
        oversized_dim_img = create_test_image(size=(200, 200))
        form.cleaned_data = {"profile_picture": oversized_dim_img}
        with pytest.raises(ValidationError) as exc:
            form.clean_profile_picture()
        assert "pixels or smaller" in str(exc.value)

    def test_clean_profile_picture_invalid_content_type(self):
        form = SiteUserCreationForm()
        txt_file = SimpleUploadedFile("fake.txt", b"not an image", content_type="text/plain")
        form.cleaned_data = {"profile_picture": txt_file}
        with pytest.raises(ValidationError):
            form.clean_profile_picture()

    def test_clean_profile_picture_oversized_bytes(self):
        form = SiteUserCreationForm()
        # Generate raw bytes larger than 20KB with valid image dimensions
        oversized_data = b"0" * (25 * 1024)
        large_file = SimpleUploadedFile("big.png", oversized_data, content_type="image/png")
        form.cleaned_data = {"profile_picture": large_file}
        with pytest.raises(ValidationError):
            form.clean_profile_picture()
