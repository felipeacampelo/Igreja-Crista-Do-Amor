from django.db.models import ProtectedError
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdminUser

from .models import Lote
from .serializers import LoteAdminSerializer, LoteSerializer


class LoteAtivoView(APIView):
    def get(self, request):
        # ativo=True nunca tem mais de uma linha (Lote.save() garante isso), mas
        # ainda pode não haver nenhum lote ativo, ou o ativo estar esgotado.
        lote = Lote.objects.filter(ativo=True).first()
        if lote is None or lote.esgotado:
            return Response(None)
        return Response(LoteSerializer(lote).data)


class LoteAdminListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]
    queryset = Lote.objects.all()
    serializer_class = LoteAdminSerializer


class LoteAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    queryset = Lote.objects.all()
    serializer_class = LoteAdminSerializer

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError({'detail': 'Não é possível excluir um lote com inscrições vinculadas.'})
