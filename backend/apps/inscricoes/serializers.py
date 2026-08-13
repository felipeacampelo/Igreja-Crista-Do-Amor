from datetime import date
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.lotes.models import Lote

from .models import Cupom, Inscricao
from .pix import payload_pix_da_inscricao
from .storage import AssinaturaUrlError, gerar_url_assinada


def _calcula_idade(data_nascimento, hoje=None):
    hoje = hoje or date.today()
    return hoje.year - data_nascimento.year - (
        (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day)
    )


class InscricaoCreateSerializer(serializers.ModelSerializer):
    cupom_codigo = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Inscricao
        fields = [
            'nome_completo', 'cpf', 'email', 'sexo', 'data_nascimento', 'celular',
            'nome_responsavel', 'celular_responsavel', 'lote', 'cupom_codigo', 'token',
        ]
        read_only_fields = ['token']

    def validate_lote(self, lote):
        if not lote.ativo:
            raise serializers.ValidationError('Lote não encontrado.')
        if lote.esgotado:
            raise serializers.ValidationError('Lote esgotado.')
        return lote

    def validate(self, attrs):
        idade = _calcula_idade(attrs['data_nascimento'])
        if idade < 18 and (not attrs.get('nome_responsavel') or not attrs.get('celular_responsavel')):
            raise serializers.ValidationError({
                'nome_responsavel': 'Obrigatório para inscritos menores de idade.',
                'celular_responsavel': 'Obrigatório para inscritos menores de idade.',
            })

        cupom_codigo = attrs.pop('cupom_codigo', '')
        if cupom_codigo:
            try:
                cupom = Cupom.objects.get(codigo=cupom_codigo.strip().upper())
            except Cupom.DoesNotExist:
                raise serializers.ValidationError({'cupom_codigo': 'Cupom inválido.'})
            if cupom.esgotado:
                raise serializers.ValidationError({'cupom_codigo': 'Cupom esgotado.'})
            attrs['cupom'] = cupom
        else:
            attrs['cupom'] = None

        return attrs

    def create(self, validated_data):
        lote = validated_data['lote']
        cupom = validated_data.get('cupom')

        # Re-checa esgotamento sob lock: a validação acima já rejeitou o caso óbvio,
        # mas sem isso duas submissões concorrentes perto do limite poderiam passar
        # ambas na validação e furar o limite de vagas/usos.
        with transaction.atomic():
            lote_travado = Lote.objects.select_for_update().get(pk=lote.pk)
            if lote_travado.esgotado:
                raise serializers.ValidationError({'lote': 'Lote esgotado.'})

            if cupom:
                cupom_travado = Cupom.objects.select_for_update().get(pk=cupom.pk)
                if cupom_travado.esgotado:
                    raise serializers.ValidationError({'cupom_codigo': 'Cupom esgotado.'})

            desconto = cupom.valor_desconto if cupom else Decimal('0')
            validated_data['preco_final'] = max(lote.preco - desconto, Decimal('0'))
            return Inscricao.objects.create(**validated_data)


class ComprovanteUploadSerializer(serializers.Serializer):
    ALLOWED_CONTENT_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf']
    MAX_SIZE_BYTES = 10 * 1024 * 1024

    arquivo = serializers.FileField()

    def validate_arquivo(self, arquivo):
        if arquivo.content_type not in self.ALLOWED_CONTENT_TYPES:
            raise serializers.ValidationError('Envie uma imagem (JPEG, PNG ou WEBP) ou um PDF.')
        if arquivo.size > self.MAX_SIZE_BYTES:
            raise serializers.ValidationError('Arquivo maior que 10MB.')
        return arquivo


class InscricaoStatusSerializer(serializers.ModelSerializer):
    lote = serializers.CharField(source='lote.nome', read_only=True)
    cupom = serializers.CharField(source='cupom.codigo', read_only=True, allow_null=True)
    pix_payload = serializers.SerializerMethodField()

    class Meta:
        model = Inscricao
        fields = [
            'nome_completo', 'lote', 'cupom', 'status', 'preco_final', 'criado_em',
            'pix_payload', 'motivo_rejeicao', 'codigo_checkin',
        ]

    def get_pix_payload(self, obj):
        return payload_pix_da_inscricao(obj)


class AdminInscricaoQueueSerializer(serializers.ModelSerializer):
    lote = serializers.CharField(source='lote.nome', read_only=True)
    cupom = serializers.CharField(source='cupom.codigo', read_only=True, allow_null=True)
    comprovante_url = serializers.SerializerMethodField()

    class Meta:
        model = Inscricao
        fields = [
            'id', 'nome_completo', 'cpf', 'email', 'celular', 'sexo', 'data_nascimento',
            'lote', 'cupom', 'preco_final', 'status', 'comprovante_url', 'criado_em',
        ]

    def get_comprovante_url(self, obj):
        if not obj.comprovante_path:
            return None
        try:
            return gerar_url_assinada(obj.comprovante_path)
        except AssinaturaUrlError:
            return None


class RejeitarInscricaoSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=500)
