import requests
from datetime import datetime, timedelta, time
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from .models import Trip, RouteSegment, ELDLog
import math

class RouteService:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="eld_trip_planner")
    
    def geocode_location(self, location_str):
        """Convert address string to coordinates"""
        try:
            location = self.geolocator.geocode(location_str)
            if location:
                return (location.latitude, location.longitude)
            return None
        except:
            return None
    
    def calculate_distance_duration(self, start_coords, end_coords):
        """Calculate distance and estimated duration between two points"""
        distance_miles = geodesic(start_coords, end_coords).miles
        # Assume average speed of 55 mph for trucking
        duration_hours = distance_miles / 55.0
        return distance_miles, duration_hours
    
    def get_route_data(self, trip):
        """Get complete route data using free routing"""
        # Geocode all locations
        current_coords = self.geocode_location(trip.current_location)
        pickup_coords = self.geocode_location(trip.pickup_location)
        dropoff_coords = self.geocode_location(trip.dropoff_location)
        
        if not all([current_coords, pickup_coords, dropoff_coords]):
            raise ValueError("Could not geocode all locations")
        
        route_segments = []
        
        # Segment 1: Current to Pickup
        dist1, dur1 = self.calculate_distance_duration(current_coords, pickup_coords)
        route_segments.append({
            'start_location': trip.current_location,
            'end_location': trip.pickup_location,
            'distance': dist1,
            'duration': dur1,
            'segment_type': 'travel'
        })
        
        # Segment 2: Pickup (1 hour)
        route_segments.append({
            'start_location': trip.pickup_location,
            'end_location': trip.pickup_location,
            'distance': 0,
            'duration': 1.0,  # 1 hour for pickup
            'segment_type': 'pickup'
        })
        
        # Segment 3: Pickup to Dropoff
        dist2, dur2 = self.calculate_distance_duration(pickup_coords, dropoff_coords)
        route_segments.append({
            'start_location': trip.pickup_location,
            'end_location': trip.dropoff_location,
            'distance': dist2,
            'duration': dur2,
            'segment_type': 'travel'
        })
        
        # Segment 4: Dropoff (1 hour)
        route_segments.append({
            'start_location': trip.dropoff_location,
            'end_location': trip.dropoff_location,
            'distance': 0,
            'duration': 1.0,  # 1 hour for dropoff
            'segment_type': 'dropoff'
        })
        
        total_distance = dist1 + dist2
        total_duration = dur1 + dur2 + 2.0  # +2 for pickup/dropoff
        
        # Add fuel stops if needed (every 1000 miles)
        fuel_stops_needed = math.floor(total_distance / 1000)
        
        return {
            'route_segments': route_segments,
            'total_distance': total_distance,
            'total_duration': total_duration,
            'fuel_stops_needed': fuel_stops_needed,
            'coordinates': {
                'current': current_coords,
                'pickup': pickup_coords,
                'dropoff': dropoff_coords
            }
        }

class ELDService:
    def __init__(self):
        # HOS Rules for property-carrying drivers (70/8 rule)
        self.MAX_DRIVING_DAILY = 11  # hours
        self.MAX_ON_DUTY_DAILY = 14  # hours
        self.MAX_ON_DUTY_WEEKLY = 70  # hours in 8 days
        self.REQUIRED_OFF_DUTY = 10  # consecutive hours
        self.REQUIRED_BREAK_AFTER = 8  # hours of driving
        self.REQUIRED_BREAK_DURATION = 0.5  # 30 minutes
    
    def generate_eld_logs(self, trip, route_data):
        """Generate ELD logs based on route and HOS rules"""
        logs = []
        current_time = datetime.now()
        current_date = current_time.date()
        current_hour = current_time.hour
        current_cycle_used = trip.current_cycle_used
        
        # Start with 10-hour off-duty period if needed
        if current_cycle_used > 0:
            off_duty_start = time(current_hour - 10 if current_hour >= 10 else current_hour + 14, 0)
            off_duty_end = time(current_hour, 0)
            
            logs.append({
                'log_date': current_date,
                'start_time': off_duty_start,
                'end_time': off_duty_end,
                'duty_status': 'OFF',
                'location': trip.current_location,
                'duration': 10.0,
                'remarks': 'Required 10-hour off-duty period'
            })
        
        # Process route segments
        segment_start_time = current_time
        driving_time_today = 0
        on_duty_time_today = 0
        cycle_hours_used = current_cycle_used
        
        for i, segment_data in enumerate(route_data['route_segments']):
            segment_duration = segment_data['duration']
            
            # Check if we need a break
            if segment_data['segment_type'] == 'travel' and driving_time_today >= self.REQUIRED_BREAK_AFTER:
                # Add 30-minute break
                logs.append({
                    'log_date': segment_start_time.date(),
                    'start_time': segment_start_time.time(),
                    'end_time': (segment_start_time + timedelta(minutes=30)).time(),
                    'duty_status': 'OFF',
                    'location': segment_data['start_location'],
                    'duration': 0.5,
                    'remarks': 'Required 30-minute break'
                })
                segment_start_time += timedelta(minutes=30)
                driving_time_today = 0  # Reset driving time after break
            
            # Check daily limits
            if segment_data['segment_type'] == 'travel':
                if driving_time_today + segment_duration > self.MAX_DRIVING_DAILY:
                    # Need 10-hour reset
                    logs.append({
                        'log_date': segment_start_time.date(),
                        'start_time': segment_start_time.time(),
                        'end_time': (segment_start_time + timedelta(hours=10)).time(),
                        'duty_status': 'OFF',
                        'location': segment_data['start_location'],
                        'duration': 10.0,
                        'remarks': 'Daily 10-hour off-duty reset'
                    })
                    segment_start_time += timedelta(hours=10)
                    driving_time_today = 0
                    on_duty_time_today = 0
                    cycle_hours_used = 0  # Weekly reset logic would be more complex
            
            # Add the actual segment log
            duty_status = self._get_duty_status(segment_data['segment_type'])
            segment_end_time = segment_start_time + timedelta(hours=segment_duration)
            
            logs.append({
                'log_date': segment_start_time.date(),
                'start_time': segment_start_time.time(),
                'end_time': segment_end_time.time(),
                'duty_status': duty_status,
                'location': segment_data['end_location'],
                'duration': segment_duration,
                'remarks': f"{segment_data['segment_type'].title()} - {segment_data.get('distance', 0):.1f} miles"
            })
            
            # Update time tracking
            if duty_status in ['D', 'ON']:
                on_duty_time_today += segment_duration
                cycle_hours_used += segment_duration
                if duty_status == 'D':
                    driving_time_today += segment_duration
            
            segment_start_time = segment_end_time
        
        return logs
    
    def _get_duty_status(self, segment_type):
        """Map segment type to ELD duty status"""
        mapping = {
            'travel': 'D',        # Driving
            'pickup': 'ON',       # On Duty (Not Driving)
            'dropoff': 'ON',      # On Duty (Not Driving)
            'fuel': 'ON',         # On Duty (Not Driving)
            'rest': 'OFF',        # Off Duty
        }
        return mapping.get(segment_type, 'ON')

class TripPlannerService:
    def __init__(self):
        self.route_service = RouteService()
        self.eld_service = ELDService()
    
    def create_trip_plan(self, trip_data):
        """Create complete trip plan with route and ELD logs"""
        # Create trip
        trip = Trip.objects.create(**trip_data)
        
        try:
            # Get route data
            route_data = self.route_service.get_route_data(trip)
            
            # Update trip with calculated data
            trip.total_distance = route_data['total_distance']
            trip.estimated_duration = route_data['total_duration']
            trip.fuel_stops_needed = route_data['fuel_stops_needed']
            trip.save()
            
            # Create route segments
            for i, segment_data in enumerate(route_data['route_segments']):
                RouteSegment.objects.create(
                    trip=trip,
                    sequence_order=i + 1,
                    **segment_data
                )
            
            # Generate ELD logs
            eld_logs_data = self.eld_service.generate_eld_logs(trip, route_data)
            
            for log_data in eld_logs_data:
                ELDLog.objects.create(
                    trip=trip,
                    **log_data
                )
            
            return {
                'trip': trip,
                'route_data': route_data,
                'success': True
            }
            
        except Exception as e:
            trip.delete()  # Clean up if planning fails
            return {
                'error': str(e),
                'success': False
            }
