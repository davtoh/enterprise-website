from django.urls import path, re_path
from . import views

app_name = 'language_management'
urlpatterns = [
    path('', views.LangView.as_view(), name="index"),
]
