from django.urls import path

from .views import (
    ComprovanteUploadView,
    IngressoDownloadView,
    InscricaoCreateView,
    InscricaoDetailView,
    PixQrCodeView,
)

urlpatterns = [
    path('', InscricaoCreateView.as_view(), name='inscricao-create'),
    path('<str:token>/', InscricaoDetailView.as_view(), name='inscricao-detail'),
    path('<str:token>/comprovante/', ComprovanteUploadView.as_view(), name='inscricao-comprovante'),
    path('<str:token>/ingresso/', IngressoDownloadView.as_view(), name='inscricao-ingresso'),
    path('<str:token>/pix-qr/', PixQrCodeView.as_view(), name='inscricao-pix-qr'),
]
