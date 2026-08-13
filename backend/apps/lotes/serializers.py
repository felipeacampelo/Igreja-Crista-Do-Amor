from rest_framework import serializers

from .models import Lote


class LoteSerializer(serializers.ModelSerializer):
    vagas_restantes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Lote
        fields = ['id', 'nome', 'preco', 'vagas_restantes']


class LoteAdminSerializer(serializers.ModelSerializer):
    vagas_ocupadas = serializers.IntegerField(read_only=True)
    vagas_restantes = serializers.IntegerField(read_only=True)
    esgotado = serializers.BooleanField(read_only=True)

    class Meta:
        model = Lote
        fields = [
            'id', 'nome', 'preco', 'limite_vagas', 'ativo',
            'vagas_ocupadas', 'vagas_restantes', 'esgotado', 'criado_em',
        ]
        read_only_fields = ['criado_em']
