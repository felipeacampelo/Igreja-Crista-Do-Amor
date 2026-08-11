from rest_framework import generics

from .models import Lote
from .serializers import LoteSerializer


class LoteListView(generics.ListAPIView):
    serializer_class = LoteSerializer

    def get_queryset(self):
        # esgotado depende de vagas_ocupadas, uma property Python (não uma coluna) —
        # por isso o filtro roda em Python, não como QuerySet. Revisitar quando
        # Inscrição existir (issue #5) e isso puder virar uma annotation/filter no DB.
        return [lote for lote in Lote.objects.filter(ativo=True) if not lote.esgotado]
