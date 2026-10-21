from django.urls import path, re_path
from . import views

app_name = 'home'
urlpatterns = [
    path('', views.home, name="index"),
    path('index.html', views.home, name="index_file"),
    path('about/', views.about, name="about"),
    path('about.html', views.about, name="about_file"),
    path('services/', views.services, name="services"),
    path('services.html', views.services, name="services_file"),
    path('products/', views.products, name="products"),
    path('products.html', views.products, name="products_file"),
    path('contact/', views.contact, name="contact"),
    path('contact.html', views.contact, name="contact_file"),
]
