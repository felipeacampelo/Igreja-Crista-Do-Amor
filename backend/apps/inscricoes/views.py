import os

from rest_framework import generics, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import PodeAprovarPagamento

from .models import Inscricao
from .serializers import (
    AdminInscricaoQueueSerializer,
    ComprovanteUploadSerializer,
    InscricaoCreateSerializer,
    InscricaoStatusSerializer,
    RejeitarInscricaoSerializer,
)
from .storage import UploadComprovanteError, upload_comprovante


class InscricaoCreateView(generics.CreateAPIView):
    serializer_class = InscricaoCreateSerializer


class InscricaoDetailView(generics.RetrieveAPIView):
    queryset = Inscricao.objects.all()
    serializer_class = InscricaoStatusSerializer
    lookup_field = 'token'


class ComprovanteUploadView(APIView):
    def post(self, request, token):
        inscricao = get_object_or_404(Inscricao, token=token)

        if inscricao.status != Inscricao.Status.PENDENTE:
            return Response(
                {'detail': 'Comprovante só pode ser enviado enquanto a inscrição está pendente.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ComprovanteUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        arquivo = serializer.validated_data['arquivo']

        extensao = os.path.splitext(arquivo.name)[1].lower()
        caminho = f'{inscricao.token}/comprovante{extensao}'

        try:
            upload_comprovante(caminho, arquivo)
        except UploadComprovanteError:
            return Response(
                {'detail': 'Não foi possível enviar o comprovante. Tente novamente.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        inscricao.comprovante_path = caminho
        inscricao.status = Inscricao.Status.COMPROVANTE_ENVIADO
        inscricao.save(update_fields=['comprovante_path', 'status', 'atualizado_em'])

        return Response(InscricaoStatusSerializer(inscricao).data)


class FilaAprovacaoView(generics.ListAPIView):
    permission_classes = [PodeAprovarPagamento]
    serializer_class = AdminInscricaoQueueSerializer
    queryset = Inscricao.objects.filter(status=Inscricao.Status.COMPROVANTE_ENVIADO)


class AprovarInscricaoView(APIView):
    permission_classes = [PodeAprovarPagamento]

    def post(self, request, pk):
        inscricao = get_object_or_404(Inscricao, pk=pk)

        if inscricao.status != Inscricao.Status.COMPROVANTE_ENVIADO:
            return Response(
                {'detail': 'Ação não permitida nesse status.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inscricao.status = Inscricao.Status.CONFIRMADA
        inscricao.save(update_fields=['status', 'atualizado_em'])

        return Response(AdminInscricaoQueueSerializer(inscricao).data)


class RejeitarInscricaoView(APIView):
    permission_classes = [PodeAprovarPagamento]

    def post(self, request, pk):
        inscricao = get_object_or_404(Inscricao, pk=pk)

        if inscricao.status != Inscricao.Status.COMPROVANTE_ENVIADO:
            return Response(
                {'detail': 'Ação não permitida nesse status.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RejeitarInscricaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        inscricao.status = Inscricao.Status.REJEITADA
        inscricao.motivo_rejeicao = serializer.validated_data['motivo']
        inscricao.save(update_fields=['status', 'motivo_rejeicao', 'atualizado_em'])

        return Response(AdminInscricaoQueueSerializer(inscricao).data)
