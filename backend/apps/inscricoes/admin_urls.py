from django.urls import path

from .views import AprovarInscricaoView, FilaAprovacaoView, RejeitarInscricaoView

urlpatterns = [
    path('fila-aprovacao/', FilaAprovacaoView.as_view(), name='fila-aprovacao'),
    path('<int:pk>/aprovar/', AprovarInscricaoView.as_view(), name='inscricao-aprovar'),
    path('<int:pk>/rejeitar/', RejeitarInscricaoView.as_view(), name='inscricao-rejeitar'),
]
