import os

from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import PodeAprovarPagamento, PodeRealizarCheckin

from .checkin import checkin_manual, checkin_via_qr
from .ingresso import build_ingresso_pdf_bytes
from .models import Inscricao
from .notificacoes import enviar_ingresso_email_seguro
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


def _inscricao_em_revisao_ou_erro(pk):
    """Carrega a inscrição ou devolve a Response de erro a retornar direto pela view."""
    inscricao = get_object_or_404(Inscricao, pk=pk)
    if inscricao.status != Inscricao.Status.COMPROVANTE_ENVIADO:
        return None, Response(
            {'detail': 'Ação não permitida nesse status.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return inscricao, None


class AprovarInscricaoView(APIView):
    permission_classes = [PodeAprovarPagamento]

    def post(self, request, pk):
        inscricao, erro = _inscricao_em_revisao_ou_erro(pk)
        if erro:
            return erro

        inscricao.status = Inscricao.Status.CONFIRMADA
        inscricao.save(update_fields=['status', 'atualizado_em'])
        enviar_ingresso_email_seguro(inscricao)

        return Response(AdminInscricaoQueueSerializer(inscricao).data)


class RejeitarInscricaoView(APIView):
    permission_classes = [PodeAprovarPagamento]

    def post(self, request, pk):
        inscricao, erro = _inscricao_em_revisao_ou_erro(pk)
        if erro:
            return erro

        serializer = RejeitarInscricaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        inscricao.status = Inscricao.Status.REJEITADA
        inscricao.motivo_rejeicao = serializer.validated_data['motivo']
        inscricao.save(update_fields=['status', 'motivo_rejeicao', 'atualizado_em'])

        return Response(AdminInscricaoQueueSerializer(inscricao).data)


class IngressoDownloadView(APIView):
    def get(self, request, token):
        inscricao = get_object_or_404(Inscricao, token=token)

        if inscricao.status != Inscricao.Status.CONFIRMADA:
            return Response(
                {'detail': 'Ingresso disponível apenas para inscrições confirmadas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pdf_bytes = build_ingresso_pdf_bytes(inscricao)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        # inline (não attachment) para permitir visualização no navegador, além de download.
        response['Content-Disposition'] = 'inline; filename="ingresso.pdf"'
        return response


def _checkin_payload(resultado, inscricao):
    return {
        'resultado': resultado,
        'nome_completo': inscricao.nome_completo if inscricao else None,
        'lote': inscricao.lote.nome if inscricao else None,
        'checkin_em': inscricao.checkin_em if inscricao else None,
    }


class ScanCheckinView(APIView):
    permission_classes = [PodeRealizarCheckin]

    def post(self, request):
        resultado, inscricao, _log = checkin_via_qr(request.data.get('token_qr', ''), request.user)
        return Response(_checkin_payload(resultado, inscricao))


class ManualCheckinView(APIView):
    permission_classes = [PodeRealizarCheckin]

    def post(self, request):
        resultado, inscricao, _log = checkin_manual(request.data.get('codigo', ''), request.user)
        return Response(_checkin_payload(resultado, inscricao))
