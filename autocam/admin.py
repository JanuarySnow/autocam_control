from django.contrib import admin
from .models import AutoCamServer, AutoCamCommand, CarState


@admin.register(AutoCamServer)
class AutoCamServerAdmin(admin.ModelAdmin):
    list_display = ['name', 'host', 'is_active', 'is_auto_registered', 'last_seen']
    list_filter = ['is_active', 'is_auto_registered']


@admin.register(AutoCamCommand)
class AutoCamCommandAdmin(admin.ModelAdmin):
    list_display = ['command', 'server', 'car_id', 'camera_id', 'is_executed', 'created_at']
    list_filter = ['command', 'is_executed']


@admin.register(CarState)
class CarStateAdmin(admin.ModelAdmin):
    list_display = ['driver_name', 'car_id', 'server', 'is_connected', 'position', 'updated_at']
    list_filter = ['is_connected']
