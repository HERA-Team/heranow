from django.contrib import admin

from .models import AntennaStatus, Antenna

# Register your models here.


admin.site.register(AntennaStatus)
admin.site.register(Antenna)
