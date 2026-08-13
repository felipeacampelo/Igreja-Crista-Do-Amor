from django.urls import path

from .views import LoteAdminDetailView, LoteAdminListCreateView

urlpatterns = [
    path('', LoteAdminListCreateView.as_view(), name='lote-admin-list'),
    path('<int:pk>/', LoteAdminDetailView.as_view(), name='lote-admin-detail'),
]
