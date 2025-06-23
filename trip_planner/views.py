from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Trip, RouteSegment, ELDLog
from .serializers import TripSerializer, TripCreateSerializer, RouteSegmentSerializer, ELDLogSerializer
from .services import TripPlannerService

class TripCreateView(APIView):
    """Create a new trip with complete planning"""
    
    def post(self, request):
        serializer = TripCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            trip_service = TripPlannerService()
            result = trip_service.create_trip_plan(serializer.validated_data)
            
            if result['success']:
                trip_serializer = TripSerializer(result['trip'])
                return Response({
                    'trip': trip_serializer.data,
                    'route_coordinates': result['route_data']['coordinates'],
                    'message': 'Trip planned successfully'
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'error': result['error']
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TripDetailView(generics.RetrieveAPIView):
    """Get trip details"""
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    lookup_field = 'id'

class TripListView(generics.ListAPIView):
    """List all trips"""
    queryset = Trip.objects.all().order_by('-created_at')
    serializer_class = TripSerializer

class RouteSegmentsView(generics.ListAPIView):
    """Get route segments for a trip"""
    serializer_class = RouteSegmentSerializer
    
    def get_queryset(self):
        trip_id = self.kwargs['trip_id']
        return RouteSegment.objects.filter(trip_id=trip_id)

class ELDLogsView(generics.ListAPIView):
    """Get ELD logs for a trip"""
    serializer_class = ELDLogSerializer
    
    def get_queryset(self):
        trip_id = self.kwargs['trip_id']
        return ELDLog.objects.filter(trip_id=trip_id)

class ELDLogSheetView(APIView):
    """Generate ELD log sheet data for visualization"""
    
    def get(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)
        logs = ELDLog.objects.filter(trip=trip)
        
        # Group logs by date for daily log sheets
        log_sheets = {}
        for log in logs:
            date_str = log.log_date.strftime('%Y-%m-%d')
            if date_str not in log_sheets:
                log_sheets[date_str] = {
                    'date': date_str,
                    'logs': [],
                    'totals': {
                        'off_duty': 0,
                        'sleeper_berth': 0,
                        'driving': 0,
                        'on_duty': 0
                    }
                }
            
            log_data = ELDLogSerializer(log).data
            log_sheets[date_str]['logs'].append(log_data)
            
            # Add to totals
            if log.duty_status == 'OFF':
                log_sheets[date_str]['totals']['off_duty'] += log.duration
            elif log.duty_status == 'SB':
                log_sheets[date_str]['totals']['sleeper_berth'] += log.duration
            elif log.duty_status == 'D':
                log_sheets[date_str]['totals']['driving'] += log.duration
            elif log.duty_status == 'ON':
                log_sheets[date_str]['totals']['on_duty'] += log.duration
        
        return Response({
            'trip_id': str(trip_id),
            'log_sheets': list(log_sheets.values())
        })

class TripSummaryView(APIView):
    """Get trip summary with key metrics"""
    
    def get(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)
        logs = ELDLog.objects.filter(trip=trip)
        
        # Calculate summary metrics
        total_driving_time = sum(log.duration for log in logs if log.duty_status == 'D')
        total_on_duty_time = sum(log.duration for log in logs if log.duty_status in ['D', 'ON'])
        total_off_duty_time = sum(log.duration for log in logs if log.duty_status == 'OFF')
        
        summary = {
            'trip_id': str(trip_id),
            'trip_details': TripSerializer(trip).data,
            'time_summary': {
                'total_driving_hours': round(total_driving_time, 2),
                'total_on_duty_hours': round(total_on_duty_time, 2),
                'total_off_duty_hours': round(total_off_duty_time, 2),
                'estimated_completion_hours': round(trip.estimated_duration or 0, 2)
            },
            'compliance_status': {
                'within_daily_driving_limit': total_driving_time <= 11,
                'within_daily_duty_limit': total_on_duty_time <= 14,
                'has_required_breaks': True  # Simplified check
            }
        }
        
        return Response(summary)


# added this route as a temporary fix, pending maps api access
@api_view(['GET'])
def calculate_route_view(request):
    # to be ideally retrieve using google's geocoder apis
    route = {
      'totalDistance': 1250,
      'totalTime': 18.5,
      'waypoints': [
        { 'name': 'Current Location', 'lat': 40.7128, 'lng': -74.0060, 'type': 'start' },
        { 'name': 'Fuel Stop - TA Travel Center', 'lat': 41.4993, 'lng': -81.6944, 'type': 'fuel', 'estimatedArrival': '2024-06-15T10:30:00' },
        { 'name': 'Pickup Location', 'lat': 41.8781, 'lng': -87.6298, 'type': 'pickup', 'estimatedArrival': '2024-06-15T14:00:00' },
        { 'name': 'Mandatory Rest Area', 'lat': 41.2524, 'lng': -95.9980, 'type': 'rest', 'estimatedArrival': '2024-06-15T22:00:00' },
        { 'name': 'Fuel Stop - Pilot Flying J', 'lat': 39.7391, 'lng': -104.9847, 'type': 'fuel', 'estimatedArrival': '2024-06-16T08:00:00' },
        { 'name': 'Dropoff Location', 'lat': 37.7749, 'lng': -122.4194, 'type': 'dropoff', 'estimatedArrival': '2024-06-16T16:30:00' }
      ],
      'fuelStops': 2,
      'restPeriods': [
        { 'start': '2024-06-15T22:00:00', 'end': '2024-06-16T08:00:00', 'duration': 10, 'type': '34-hour reset' }
      ]
    }
    
    logSheets = [
      {
        'date': '2024-06-15',
        'drivingTime': 8,
        'onDutyTime': 10,
        'restTime': 14,
        'violations': [],
        'entries': [
          { 'time': '06:00', 'status': 'off-duty', 'location': 'Current Location' },
          { 'time': '08:00', 'status': 'on-duty', 'location': 'Pre-trip inspection' },
          { 'time': '09:00', 'status': 'driving', 'location': 'En route to pickup' },
          { 'time': '14:00', 'status': 'on-duty', 'location': 'Pickup - Loading' },
          { 'time': '15:00', 'status': 'driving', 'location': 'En route to delivery' },
          { 'time': '22:00', 'status': 'off-duty', 'location': 'Rest area - Mandatory rest' }
        ]
      },
      {
        'date': '2024-06-16',
        'drivingTime': 6.5,
        'onDutyTime': 8.5,
        'restTime': 15.5,
        'violations': [],
        'entries': [
          { 'time': '08:00', 'status': 'off-duty', 'location': 'Rest area' },
          { 'time': '08:30', 'status': 'on-duty', 'location': 'Pre-trip inspection' },
          { 'time': '09:00', 'status': 'driving', 'location': 'En route to delivery' },
          { 'time': '15:30', 'status': 'on-duty', 'location': 'Delivery - Unloading' },
          { 'time': '16:30', 'status': 'off-duty', 'location': 'Delivery complete' }
        ]
      }
    ]

    mockData = {
        'route' : route,
        'logSheets' : logSheets
    }

    return Response(mockData)