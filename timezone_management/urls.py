from django.urls import path
from . import views

app_name = 'timezone_management'

urlpatterns = [
    path('set/', views.set_timezone, name='set_timezone'),
]
