from django.contrib import admin
from django.http.request import HttpRequest
from .models import *
from guardian.admin import GuardedModelAdmin

# Register your models here.
class LocationAdmin(GuardedModelAdmin):
    pass

admin.site.register(Location, LocationAdmin)
#admin.site.register(Kalip)
admin.site.register(Hareket)
#@admin.register(Hareket)
