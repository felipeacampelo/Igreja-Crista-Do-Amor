from django.urls import path

from .views import LoteListView

urlpatterns = [
    path('', LoteListView.as_view(), name='lote-list'),
]
