from django.core.validators import MinValueValidator
from django.db import models


class Lote(models.Model):
    nome = models.CharField('Nome', max_length=100)
    preco = models.DecimalField(
        'Preço',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    limite_vagas = models.PositiveIntegerField('Limite de vagas')
    ativo = models.BooleanField('Ativo', default=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Lote'
        verbose_name_plural = 'Lotes'
        ordering = ['preco']

    def __str__(self):
        return self.nome

    @property
    def vagas_ocupadas(self):
        # Inscrição ainda não existe (issue #5) — sem inscrições vinculadas, sempre 0 por ora.
        return 0

    @property
    def vagas_restantes(self):
        return self.limite_vagas - self.vagas_ocupadas

    @property
    def esgotado(self):
        return self.vagas_restantes <= 0
