from django.urls import path

from .views import ComprovanteUploadView, InscricaoCreateView, InscricaoDetailView

urlpatterns = [
    path('', InscricaoCreateView.as_view(), name='inscricao-create'),
    path('<str:token>/', InscricaoDetailView.as_view(), name='inscricao-detail'),
    path('<str:token>/comprovante/', ComprovanteUploadView.as_view(), name='inscricao-comprovante'),
]
