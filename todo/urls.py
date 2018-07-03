from django.urls import path, re_path
from . import views

app_name = 'todo'
urlpatterns = [
    path('', views.index, name="index"),
    re_path('^details/(?P<id>\w+)/$', views.details, name="details"),
    path('add', views.add, name="add"),
]
