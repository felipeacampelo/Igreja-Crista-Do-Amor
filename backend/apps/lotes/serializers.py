from rest_framework import serializers

from .models import Lote


class LoteSerializer(serializers.ModelSerializer):
    vagas_restantes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Lote
        fields = ['id', 'nome', 'preco', 'vagas_restantes']
