from django.urls import path

from .views import InscricaoCreateView, InscricaoDetailView

urlpatterns = [
    path('', InscricaoCreateView.as_view(), name='inscricao-create'),
    path('<str:token>/', InscricaoDetailView.as_view(), name='inscricao-detail'),
]
