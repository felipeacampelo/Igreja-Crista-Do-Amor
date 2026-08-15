import logging
import os
import re
from decimal import Decimal
from io import BytesIO

import qrcode
from django.db.models import F, ProtectedError, Q, Sum, Value
from django.db.models.functions import Replace
from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter
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
    AdminInscricaoListSerializer,
    AdminInscricaoQueueSerializer,
    AlterarStatusInscricaoSerializer,
    ComprovanteUploadSerializer,
    CupomAdminSerializer,
    InscricaoCreateSerializer,
    InscricaoStatusSerializer,
    RejeitarInscricaoSerializer,
)
from .storage import AssinaturaUrlError, UploadComprovanteError, gerar_url_assinada, upload_comprovante

logger = logging.getLogger('apps.inscricoes')


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
        except UploadComprovanteError as exc:
            # A mensagem pro usuário é deliberadamente genérica (não expõe detalhe
            # de infra) — o motivo real (ex: credencial inválida, bucket
            # inexistente) só existe aqui, senão fica impossível diagnosticar em
            # produção sem acesso ao Supabase.
            logger.error('Falha no upload de comprovante inscricao_id=%s: %s', inscricao.id, exc)
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


class AdminInscricaoListView(generics.ListAPIView):
    """Listagem completa (todos os status), com busca, filtro e ordenação."""

    permission_classes = [PodeAprovarPagamento]
    serializer_class = AdminInscricaoListSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ['nome_completo', 'criado_em', 'status', 'preco_final', 'lote__nome']
    # '-id' como desempate: várias inscrições podem ter o mesmo criado_em (ou o
    # mesmo nome/lote), e sem critério estável a ordem entre elas varia de uma
    # requisição pra outra.
    ordering = ['-criado_em', '-id']

    def get_queryset(self):
        queryset = Inscricao.objects.select_related('lote', 'cupom')

        situacoes = [s for s in self.request.query_params.get('status', '').split(',') if s]
        if situacoes:
            queryset = queryset.filter(status__in=situacoes)

        busca = self.request.query_params.get('q', '').strip()
        if busca:
            filtro = (
                Q(nome_completo__icontains=busca)
                | Q(email__icontains=busca)
                | Q(cpf__icontains=busca)
                | Q(codigo_checkin__iexact=busca)
            )
            # CPF é gravado formatado (000.000.000-00); uma busca digitada só com
            # números não casaria no icontains acima — compara também contra a
            # versão sem pontuação.
            digitos = re.sub(r'\D', '', busca)
            if digitos:
                queryset = queryset.annotate(
                    cpf_digitos=Replace(
                        Replace(F('cpf'), Value('.'), Value('')), Value('-'), Value('')
                    ),
                )
                filtro |= Q(cpf_digitos__contains=digitos)
            queryset = queryset.filter(filtro)

        return queryset


class AlterarStatusInscricaoView(APIView):
    """
    Correção manual de veredito pelo aprovador — diferente de
    Aprovar/RejeitarInscricaoView, aceita qualquer status de origem (serve pra
    desfazer um engano, não só pra decidir a fila).
    """

    permission_classes = [PodeAprovarPagamento]

    def post(self, request, pk):
        inscricao = get_object_or_404(Inscricao, pk=pk)

        serializer = AlterarStatusInscricaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        novo_status = serializer.validated_data['status']
        motivo = serializer.validated_data.get('motivo', '').strip()

        if novo_status == inscricao.status:
            return Response(
                {'detail': 'A inscrição já está nesse status.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Já entrou no evento: tirar de confirmada deixaria um check-in registrado
        # para uma inscrição que o sistema não considera mais válida.
        if inscricao.checkin_em and novo_status != Inscricao.Status.CONFIRMADA:
            return Response(
                {'detail': 'Inscrição já fez check-in; não é possível alterar o status.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        era_confirmada = inscricao.status == Inscricao.Status.CONFIRMADA
        inscricao.status = novo_status
        inscricao.motivo_rejeicao = motivo if novo_status == Inscricao.Status.REJEITADA else ''
        inscricao.save(update_fields=['status', 'motivo_rejeicao', 'atualizado_em'])

        # Só manda ingresso quando a inscrição passa a ser confirmada agora —
        # sem isso, corrigir qualquer outro campo de uma já confirmada reenviaria
        # o e-mail.
        if novo_status == Inscricao.Status.CONFIRMADA and not era_confirmada:
            enviar_ingresso_email_seguro(inscricao)

        return Response(AdminInscricaoListSerializer(inscricao).data)


class ComprovanteUrlView(APIView):
    """URL assinada sob demanda — a listagem só informa se existe comprovante."""

    permission_classes = [PodeAprovarPagamento]

    def get(self, request, pk):
        inscricao = get_object_or_404(Inscricao, pk=pk)
        if not inscricao.comprovante_path:
            return Response(
                {'detail': 'Inscrição sem comprovante anexado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            return Response({'url': gerar_url_assinada(inscricao.comprovante_path)})
        except AssinaturaUrlError as exc:
            logger.error('Falha ao assinar comprovante inscricao_id=%s: %s', inscricao.id, exc)
            return Response(
                {'detail': 'Não foi possível abrir o comprovante. Tente novamente.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )


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
