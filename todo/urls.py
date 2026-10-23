from django.urls import path, re_path
from . import views

app_name = 'todo'
urlpatterns = [
    path('', views.index, name="index"),
    re_path(r'^details/(?P<id>\w+)/$', views.details, name="details"),
    re_path(r'^delete/(?P<id>\w+)/$', views.delete, name="delete"),
    path('add', views.add, name="add"),
]

