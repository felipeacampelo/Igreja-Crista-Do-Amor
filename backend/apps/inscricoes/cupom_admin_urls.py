from django.urls import path

from .views import CupomAdminDetailView, CupomAdminListCreateView

urlpatterns = [
    path('', CupomAdminListCreateView.as_view(), name='cupom-admin-list'),
    path('<int:pk>/', CupomAdminDetailView.as_view(), name='cupom-admin-detail'),
]
