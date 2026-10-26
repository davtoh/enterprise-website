from django.contrib import admin
from .models import Countries, States, Cities, Location


@admin.register(Countries)
class CountriesAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(States)
class StatesAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "country")
    list_filter = ("country",)
    search_fields = ("name", "code")


@admin.register(Cities)
class CitiesAdmin(admin.ModelAdmin):
    list_display = ("name", "state", "country", "latitude", "longitude")
    list_filter = ("country", "state")
    search_fields = ("name",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "city", "is_active", "created_at")
    list_filter = ("is_active", "city__country")
    search_fields = ("name", "code", "address")
