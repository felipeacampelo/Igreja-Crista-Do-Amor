from rest_framework import generics

from .models import Lote
from .serializers import LoteSerializer


class LoteListView(generics.ListAPIView):
    serializer_class = LoteSerializer

    def get_queryset(self):
        return [lote for lote in Lote.objects.filter(ativo=True) if not lote.esgotado]
