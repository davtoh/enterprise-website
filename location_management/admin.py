from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm
from .models import Countries, States, Cities, Location
from .resources import (
    CitiesResource,
    CountriesResource,
    LocationResource,
    StatesResource,
)


@admin.register(Countries)
class CountriesAdmin(UnfoldModelAdmin, ImportExportModelAdmin):
    resource_classes = [CountriesResource]
    import_form_class = ImportForm
    export_form_class = ExportForm
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(States)
class StatesAdmin(UnfoldModelAdmin, ImportExportModelAdmin):
    resource_classes = [StatesResource]
    import_form_class = ImportForm
    export_form_class = ExportForm
    list_display = ("name", "code", "country")
    list_filter = ("country",)
    search_fields = ("name", "code")


@admin.register(Cities)
class CitiesAdmin(UnfoldModelAdmin, ImportExportModelAdmin):
    resource_classes = [CitiesResource]
    import_form_class = ImportForm
    export_form_class = ExportForm
    list_display = ("name", "state", "country", "latitude", "longitude")
    list_filter = ("country", "state")
    search_fields = ("name",)


@admin.register(Location)
class LocationAdmin(UnfoldModelAdmin, ImportExportModelAdmin):
    resource_classes = [LocationResource]
    import_form_class = ImportForm
    export_form_class = ExportForm
    list_display = ("name", "code", "city", "is_active", "created_at")
    list_filter = ("is_active", "city__country")
    search_fields = ("name", "code", "address")
