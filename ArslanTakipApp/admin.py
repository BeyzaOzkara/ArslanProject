from django import forms
from django.contrib import admin
from django.http.request import HttpRequest
from .models import *
from guardian.admin import GuardedModelAdmin

# Register your models here.
class LocationChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.locationRelationID.locationName} > {obj.locationName}" if obj.locationRelationID else obj.locationName


class LocationAdmin(GuardedModelAdmin):
    list_display = ('get_location_relation', 'locationName')

    def get_location_relation(self, obj):
        if obj.locationRelationID:
            return f"{obj.locationRelationID.locationName} > {obj.locationName}"
        return obj.locationName
    get_location_relation.short_description = 'Location Relation'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "locationRelationID":
            return LocationChoiceField(
                queryset=Location.objects.all(),
                widget=forms.Select(attrs={'size': '10'}),
                label=db_field.verbose_name,
                required=not db_field.blank,
                help_text=db_field.help_text,
                limit_choices_to=db_field.get_limit_choices_to(),
                empty_label="(None)"
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(Location, LocationAdmin)
#admin.site.register(Kalip)
admin.site.register(Hareket)
#@admin.register(Hareket)

admin.site.register(Parameter)

class YudaFormAdmin(GuardedModelAdmin):
    # Your admin customization here
    list_display = ('YudaNo', 'ProjeYoneticisi', 'Tarih', 'RevTarih')  # Example: Customize list display
    search_fields = ('YudaNo', 'MusteriFirmaAdi')  # Example: Add search fields

admin.site.register(YudaForm, YudaFormAdmin)