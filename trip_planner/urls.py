from django.urls import path
from .views import (
    TripCreateView, TripDetailView, TripListView,
    RouteSegmentsView, ELDLogsView, ELDLogSheetView, TripSummaryView, CalculateRouteView, calculate_route_view
)

urlpatterns = [
    # Trip management
    path('trips/', TripListView.as_view(), name='trip-list'),
    path('trips/create/', TripCreateView.as_view(), name='trip-create'),
    path('trips/<uuid:id>/', TripDetailView.as_view(), name='trip-detail'),
    path('trips/<uuid:trip_id>/summary/', TripSummaryView.as_view(), name='trip-summary'),
    
    # Route data
    path('trips/<uuid:trip_id>/route/', RouteSegmentsView.as_view(), name='route-segments'),
    
    # ELD logs
    path('trips/<uuid:trip_id>/logs/', ELDLogsView.as_view(), name='eld-logs'),
    path('trips/<uuid:trip_id>/log-sheets/', ELDLogSheetView.as_view(), name='eld-log-sheets'),
    path('route/calculate/', calculate_route_view, name='calculate-route')
]
