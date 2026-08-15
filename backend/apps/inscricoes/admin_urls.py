from django.urls import path

from .views import (
    AdminInscricaoListView,
    AlterarStatusInscricaoView,
    AprovarInscricaoView,
    ComprovanteUrlView,
    FilaAprovacaoView,
    RejeitarInscricaoView,
)

urlpatterns = [
    path('', AdminInscricaoListView.as_view(), name='inscricao-admin-list'),
    path('fila-aprovacao/', FilaAprovacaoView.as_view(), name='fila-aprovacao'),
    path('<int:pk>/aprovar/', AprovarInscricaoView.as_view(), name='inscricao-aprovar'),
    path('<int:pk>/rejeitar/', RejeitarInscricaoView.as_view(), name='inscricao-rejeitar'),
    path('<int:pk>/status/', AlterarStatusInscricaoView.as_view(), name='inscricao-alterar-status'),
    path('<int:pk>/comprovante-url/', ComprovanteUrlView.as_view(), name='inscricao-comprovante-url'),
]
