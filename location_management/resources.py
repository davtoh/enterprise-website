from import_export import resources
from .models import Cities, Countries, Location, States


class CountriesResource(resources.ModelResource):
    """Import/export resource for Countries."""

    class Meta:
        model = Countries
        import_id_fields = ("id",)
        fields = ("id", "name", "code")
        export_order = fields


class StatesResource(resources.ModelResource):
    """Import/export resource for States."""

    class Meta:
        model = States
        import_id_fields = ("id",)
        fields = ("id", "country", "name", "code")
        export_order = fields


class CitiesResource(resources.ModelResource):
    """Import/export resource for Cities."""

    class Meta:
        model = Cities
        import_id_fields = ("id",)
        fields = ("id", "country", "state", "name", "latitude", "longitude")
        export_order = fields


class LocationResource(resources.ModelResource):
    """Import/export resource for physical Locations."""

    class Meta:
        model = Location
        import_id_fields = ("id",)
        fields = (
            "id",
            "name",
            "code",
            "city",
            "address",
            "latitude",
            "longitude",
            "is_active",
            "created_at",
        )
        export_order = fields
