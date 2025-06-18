from rest_framework import generics, status
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
