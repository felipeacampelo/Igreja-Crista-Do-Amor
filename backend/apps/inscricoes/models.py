import secrets

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.lotes.models import Lote


def gerar_token():
    return secrets.token_urlsafe(24)


# Sem 0/O/1/I/L: caracteres que se confundem na digitação manual no check-in.
CODIGO_CHECKIN_ALFABETO = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'


def gerar_codigo_checkin():
    while True:
        codigo = ''.join(secrets.choice(CODIGO_CHECKIN_ALFABETO) for _ in range(6))
        if not Inscricao.objects.filter(codigo_checkin=codigo).exists():
            return codigo


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
    # Código curto para digitar manualmente no check-in — 'token' é longo demais
    # para isso (é usado no link público da inscrição, precisa ser difícil de adivinhar).
    # Gerado em save() (não via default=), pois a geração consulta o banco para
    # garantir unicidade e um default de campo não pode fazer isso com segurança.
    codigo_checkin = models.CharField('Código de check-in', max_length=6, unique=True, editable=False)
    comprovante_path = models.CharField('Caminho do comprovante', max_length=255, blank=True)
    motivo_rejeicao = models.CharField('Motivo da rejeição', max_length=500, blank=True)

    # Check-in é ortogonal ao status de pagamento (uma inscrição confirmada
    # segue "confirmada" antes e depois do check-in) — checkin_em presente é
    # o que marca o ingresso como já utilizado.
    checkin_em = models.DateTimeField('Check-in em', null=True, blank=True)
    checkin_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='checkins_realizados', verbose_name='Check-in por',
    )

    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Inscrição'
        verbose_name_plural = 'Inscrições'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.nome_completo} - {self.lote.nome}'

    def save(self, *args, **kwargs):
        if not self.codigo_checkin:
            self.codigo_checkin = gerar_codigo_checkin()
        super().save(*args, **kwargs)


class CheckinAuditLog(models.Model):
    class Resultado(models.TextChoices):
        ACEITA = 'aceita', 'Aceita'
        DUPLICADA = 'duplicada', 'Duplicada'
        BLOQUEADA = 'bloqueada', 'Bloqueada'

    inscricao = models.ForeignKey(
        Inscricao, on_delete=models.PROTECT, related_name='checkin_logs',
        null=True, blank=True, verbose_name='Inscrição',
    )
    resultado = models.CharField('Resultado', max_length=20, choices=Resultado.choices)
    codigo_tentado = models.CharField('Código tentado', max_length=255, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name='Usuário',
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Log de check-in'
        verbose_name_plural = 'Logs de check-in'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.resultado} - {self.usuario} - {self.criado_em}'
