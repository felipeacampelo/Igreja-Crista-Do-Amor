from rest_framework import generics

from .models import Inscricao
from .serializers import InscricaoCreateSerializer, InscricaoStatusSerializer


class InscricaoCreateView(generics.CreateAPIView):
    serializer_class = InscricaoCreateSerializer


class InscricaoDetailView(generics.RetrieveAPIView):
    queryset = Inscricao.objects.all()
    serializer_class = InscricaoStatusSerializer
    lookup_field = 'token'
