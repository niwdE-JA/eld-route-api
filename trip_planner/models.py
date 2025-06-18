from django.db import models
from django.utils import timezone
import uuid

class Trip(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    current_cycle_used = models.FloatField()  # Hours already used in current cycle
    created_at = models.DateTimeField(default=timezone.now)
    
    # Calculated fields
    total_distance = models.FloatField(null=True, blank=True)
    estimated_duration = models.FloatField(null=True, blank=True)  # Hours
    fuel_stops_needed = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"Trip {self.id} - {self.pickup_location} to {self.dropoff_location}"

class RouteSegment(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='route_segments')
    sequence_order = models.IntegerField()
    start_location = models.CharField(max_length=255)
    end_location = models.CharField(max_length=255)
    distance = models.FloatField()  # Miles
    duration = models.FloatField()  # Hours
    segment_type = models.CharField(max_length=50, choices=[
        ('travel', 'Travel'),
        ('pickup', 'Pickup'),
        ('dropoff', 'Dropoff'),
        ('fuel', 'Fuel Stop'),
        ('rest', 'Rest Break'),
    ])
    
    class Meta:
        ordering = ['sequence_order']

class ELDLog(models.Model):
    DUTY_STATUS_CHOICES = [
        ('OFF', 'Off Duty'),
        ('SB', 'Sleeper Berth'),
        ('D', 'Driving'),
        ('ON', 'On Duty (Not Driving)'),
    ]
    
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='eld_logs')
    log_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    duty_status = models.CharField(max_length=3, choices=DUTY_STATUS_CHOICES)
    location = models.CharField(max_length=255)
    odometer_start = models.IntegerField(null=True, blank=True)
    odometer_end = models.IntegerField(null=True, blank=True)
    duration = models.FloatField()  # Hours
    remarks = models.TextField(blank=True)
    
    class Meta:
        ordering = ['log_date', 'start_time']