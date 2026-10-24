from django.urls import path
from . import views

app_name = 'theme_management'

urlpatterns = [
    path('set/<str:theme_name>/', views.set_theme, name='set_theme'),
    path('set/', views.set_theme, name='set_theme_form'),
]
