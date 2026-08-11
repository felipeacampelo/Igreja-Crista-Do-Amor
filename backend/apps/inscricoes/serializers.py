from datetime import date
from decimal import Decimal

from rest_framework import serializers

from .models import Cupom, Inscricao


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
        desconto = cupom.valor_desconto if cupom else Decimal('0')
        validated_data['preco_final'] = max(lote.preco - desconto, Decimal('0'))
        return Inscricao.objects.create(**validated_data)


class InscricaoStatusSerializer(serializers.ModelSerializer):
    lote = serializers.CharField(source='lote.nome', read_only=True)
    cupom = serializers.CharField(source='cupom.codigo', read_only=True, allow_null=True)

    class Meta:
        model = Inscricao
        fields = [
            'nome_completo', 'lote', 'cupom', 'status', 'preco_final', 'criado_em',
        ]
