import secrets

from django.core.validators import MinValueValidator
from django.db import models

from apps.lotes.models import Lote


def gerar_token():
    return secrets.token_urlsafe(24)


class Cupom(models.Model):
    codigo = models.CharField('Código', max_length=50, unique=True)
    valor_desconto = models.DecimalField(
        'Valor de desconto',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    limite_usos = models.PositiveIntegerField('Limite de usos')
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Cupom'
        verbose_name_plural = 'Cupons'

    def __str__(self):
        return self.codigo

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.strip().upper()
        super().save(*args, **kwargs)

    @property
    def usos_count(self):
        return self.inscricoes.exclude(status=Inscricao.Status.REJEITADA).count()

    @property
    def esgotado(self):
        return self.usos_count >= self.limite_usos


class Inscricao(models.Model):
    class Status(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        COMPROVANTE_ENVIADO = 'comprovante_enviado', 'Comprovante enviado'
        CONFIRMADA = 'confirmada', 'Confirmada'
        REJEITADA = 'rejeitada', 'Rejeitada'

    class Origem(models.TextChoices):
        FORMULARIO = 'formulario', 'Formulário'
        IMPORTACAO = 'importacao', 'Importação'

    class Sexo(models.TextChoices):
        MASCULINO = 'M', 'Masculino'
        FEMININO = 'F', 'Feminino'

    nome_completo = models.CharField('Nome completo', max_length=200)
    cpf = models.CharField('CPF', max_length=14)
    email = models.EmailField('E-mail')
    sexo = models.CharField('Sexo', max_length=1, choices=Sexo.choices)
    data_nascimento = models.DateField('Data de nascimento')
    celular = models.CharField('Celular', max_length=20)

    nome_responsavel = models.CharField('Nome do responsável', max_length=200, blank=True)
    celular_responsavel = models.CharField('Celular do responsável', max_length=20, blank=True)

    lote = models.ForeignKey(Lote, on_delete=models.PROTECT, related_name='inscricoes', verbose_name='Lote')
    cupom = models.ForeignKey(
        Cupom, on_delete=models.PROTECT, related_name='inscricoes', verbose_name='Cupom',
        null=True, blank=True,
    )
    preco_final = models.DecimalField('Preço final', max_digits=10, decimal_places=2)

    status = models.CharField('Status', max_length=20, choices=Status.choices, default=Status.PENDENTE)
    origem = models.CharField('Origem', max_length=20, choices=Origem.choices, default=Origem.FORMULARIO)
    token = models.CharField(max_length=40, default=gerar_token, unique=True, editable=False)
    comprovante_path = models.CharField('Caminho do comprovante', max_length=255, blank=True)
    motivo_rejeicao = models.CharField('Motivo da rejeição', max_length=500, blank=True)

    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Inscrição'
        verbose_name_plural = 'Inscrições'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.nome_completo} - {self.lote.nome}'
