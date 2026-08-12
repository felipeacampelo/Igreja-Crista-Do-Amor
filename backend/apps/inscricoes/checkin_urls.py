from django.urls import path

from .views import ManualCheckinView, ScanCheckinView

urlpatterns = [
    path('scan/', ScanCheckinView.as_view(), name='checkin-scan'),
    path('manual/', ManualCheckinView.as_view(), name='checkin-manual'),
]
