from django.contrib import admin
from .models import Trip, RouteSegment, ELDLog

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('id', 'pickup_location', 'dropoff_location', 'total_distance', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('pickup_location', 'dropoff_location', 'current_location')
    readonly_fields = ('id', 'created_at')

@admin.register(RouteSegment)
class RouteSegmentAdmin(admin.ModelAdmin):
    list_display = ('trip', 'sequence_order', 'segment_type', 'distance', 'duration')
    list_filter = ('segment_type',)
    ordering = ('trip', 'sequence_order')

@admin.register(ELDLog)
class ELDLogAdmin(admin.ModelAdmin):
    list_display = ('trip', 'log_date', 'start_time', 'end_time', 'duty_status', 'duration')
    list_filter = ('duty_status', 'log_date')
    ordering = ('trip', 'log_date', 'start_time')
