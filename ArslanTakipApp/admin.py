from django import forms
from django.contrib import admin
from django.db import models
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


class MailReportRouteInline(admin.TabularInline):
    model = MailReportRoute
    extra = 0
    fields = ('route_key', 'is_active', 'to_addresses', 'cc_addresses')
    formfield_overrides = {models.TextField: {'widget': forms.Textarea(attrs={'rows': 3, 'cols': 40})}}


@admin.register(MailReportSettings)
class MailReportSettingsAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'to_addresses', 'cc_addresses', 'sender_addresses')
    readonly_fields = ('code', 'updated_at')
    fieldsets = (
        (None, {'fields': ('code', 'name', 'is_active')}),
        ('Dağıtım listesi', {'fields': ('to_addresses', 'cc_addresses')}),
        ('Tetikleme ve deneme', {'fields': ('sender_addresses', 'test_sender_addresses')}),
        ('Kayıt bilgisi', {'fields': ('updated_at',)}),
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj and obj.code != 'sevkiyat':
            fieldsets = tuple(section for section in fieldsets if section[0] != 'Tetikleme ve deneme')
        if obj and obj.code in ('die_transfer', 'die_test'):
            dynamic_field = 'include_actor' if obj.code == 'die_transfer' else 'include_representative'
            fieldsets += (('Harekete göre dağıtım', {
                'fields': (dynamic_field,),
                'description': 'Üstteki ortak TO/CC listelerine, aşağıdaki ilgili pres satırının adresleri eklenir. '
                               'Bir presi pasife almak o hedef için bütün gönderimi durdurur.',
            }),)
        return fieldsets

    def get_inlines(self, request, obj=None):
        return [MailReportRouteInline] if obj and obj.code in ('die_transfer', 'die_test') else []

    def has_add_permission(self, request):
        # Desteklenen raporlar migration ile oluşturulur.
        return False

    def has_delete_permission(self, request, obj=None):
        # Ayar kaydını silmek yerine gönderim pasife alınabilir.
        return False
