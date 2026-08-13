from django.urls import path

from .views import LoteAtivoView

urlpatterns = [
    path('', LoteAtivoView.as_view(), name='lote-ativo'),
]
