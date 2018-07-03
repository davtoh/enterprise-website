from django.contrib import admin

# Register your models here.
# import models
from .models import Todo

# register apps to appear in admin
admin.site.register(Todo)
