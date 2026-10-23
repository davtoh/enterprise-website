from django.urls import path
from . import views

urlpatterns = [
    path('set/', views.set_timezone, name='set_timezone'),
]
