import os
from decimal import Decimal
from io import BytesIO

import qrcode
from django.db.models import ProtectedError, Sum
from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.lotes.models import Lote
from apps.lotes.serializers import LoteSerializer
from apps.users.permissions import IsAdminUser, PodeAprovarPagamento, PodeRealizarCheckin

from .checkin import checkin_manual, checkin_via_qr
from .ingresso import build_ingresso_pdf_bytes
from .models import Cupom, Inscricao
from .notificacoes import enviar_ingresso_email_seguro
from .pix import payload_pix_da_inscricao
from .serializers import (
    AdminInscricaoQueueSerializer,
    ComprovanteUploadSerializer,
    CupomAdminSerializer,
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


class PixQrCodeView(APIView):
    def get(self, request, token):
        inscricao = get_object_or_404(Inscricao, token=token)

        qr_image = qrcode.make(payload_pix_da_inscricao(inscricao), box_size=6, border=2)
        buffer = BytesIO()
        qr_image.save(buffer, format='PNG')
        return HttpResponse(buffer.getvalue(), content_type='image/png')


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


class CupomAdminListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]
    queryset = Cupom.objects.all().order_by('codigo')
    serializer_class = CupomAdminSerializer


class CupomAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    queryset = Cupom.objects.all()
    serializer_class = CupomAdminSerializer

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError({'detail': 'Não é possível excluir um cupom com inscrições vinculadas.'})


class DashboardView(APIView):
    permission_classes = [PodeAprovarPagamento]

    def get(self, request):
        inscricoes_validas = Inscricao.objects.exclude(status=Inscricao.Status.REJEITADA)
        confirmadas = inscricoes_validas.filter(status=Inscricao.Status.CONFIRMADA)
        aguardando_revisao = inscricoes_validas.filter(
            status__in=[Inscricao.Status.PENDENTE, Inscricao.Status.COMPROVANTE_ENVIADO],
        )
        rejeitadas = Inscricao.objects.filter(status=Inscricao.Status.REJEITADA)

        receita_confirmada = confirmadas.aggregate(total=Sum('preco_final'))['total'] or Decimal('0')
        receita_pendente = aguardando_revisao.aggregate(total=Sum('preco_final'))['total'] or Decimal('0')

        lote_ativo = Lote.objects.filter(ativo=True).first()

        return Response({
            'inscricoes': {
                'confirmadas': confirmadas.count(),
                'aguardando_revisao': aguardando_revisao.count(),
                'rejeitadas': rejeitadas.count(),
            },
            'receita': {
                # str(Decimal) não preserva casas decimais depois de Sum() em SQLite
                # (ex.: 300 em vez de 300.00) — formata explicitamente.
                'confirmada': f'{receita_confirmada:.2f}',
                'pendente': f'{receita_pendente:.2f}',
            },
            'checkin': {
                'feitos': confirmadas.filter(checkin_em__isnull=False).count(),
                'confirmadas': confirmadas.count(),
            },
            'lote_ativo': LoteSerializer(lote_ativo).data if lote_ativo else None,
        })


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
