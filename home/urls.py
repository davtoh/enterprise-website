from django.urls import path, re_path
from . import views

app_name = 'home'
urlpatterns = [
    path('', views.home, name="index"),
    path('index.html', views.home, name="index_file"),
]
