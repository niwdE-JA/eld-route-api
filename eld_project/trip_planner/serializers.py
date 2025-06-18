from rest_framework import serializers
from .models import Trip, RouteSegment, ELDLog

class RouteSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RouteSegment
        fields = '__all__'

class ELDLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ELDLog
        fields = '__all__'

class TripSerializer(serializers.ModelSerializer):
    route_segments = RouteSegmentSerializer(many=True, read_only=True)
    eld_logs = ELDLogSerializer(many=True, read_only=True)
    
    class Meta:
        model = Trip
        fields = '__all__'

class TripCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = ['current_location', 'pickup_location', 'dropoff_location', 'current_cycle_used']
