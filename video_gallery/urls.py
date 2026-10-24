from django.urls import path
from . import views

app_name = "video_gallery"

urlpatterns = [
    path("", views.GalleryListView.as_view(), name="gallery_list"),
    path("<slug:slug>/", views.GalleryDetailView.as_view(), name="gallery_detail"),
    path("video/<int:pk>/modal/", views.VideoItemModalView.as_view(), name="video_modal"),
]
