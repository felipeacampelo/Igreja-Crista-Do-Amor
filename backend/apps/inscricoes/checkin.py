"""
Validação de check-in — replica o padrão de apps/checkin + apps/tickets do
Mio-Festa-2026 (resolve o código do QR ou digitado manualmente, transiciona
para "usado", bloqueia duplicado).

QR e código manual usam campos diferentes: o QR carrega Inscricao.token (é a
câmera que lê, então o tamanho não importa) e o código manual usa
Inscricao.codigo_checkin, mais curto para digitar na hora do check-in.

Diferente do Mio-Festa-2026, aqui TODA tentativa gera um CheckinAuditLog —
aceita, duplicada ou bloqueada — não só as aceitas, conforme exigido pela
spec (issue #1: "registro de cada tentativa... sucesso, duplicado, bloqueado").
"""
from django.utils import timezone

from .models import CheckinAuditLog, Inscricao


def checkin_via_qr(token_qr, usuario):
    inscricao = Inscricao.objects.filter(token=token_qr).first()
    return _processar(inscricao, usuario, token_qr)


def checkin_manual(codigo, usuario):
    codigo_normalizado = codigo.strip().upper()
    inscricao = Inscricao.objects.filter(codigo_checkin=codigo_normalizado).first()
    return _processar(inscricao, usuario, codigo_normalizado)


def _processar(inscricao, usuario, codigo_tentado):
    if inscricao is None or inscricao.status != Inscricao.Status.CONFIRMADA:
        resultado = CheckinAuditLog.Resultado.BLOQUEADA
    elif inscricao.checkin_em is not None:
        resultado = CheckinAuditLog.Resultado.DUPLICADA
    else:
        resultado = CheckinAuditLog.Resultado.ACEITA
        inscricao.checkin_em = timezone.now()
        inscricao.checkin_por = usuario
        inscricao.save(update_fields=['checkin_em', 'checkin_por'])

    log = CheckinAuditLog.objects.create(
        inscricao=inscricao, usuario=usuario, resultado=resultado,
        codigo_tentado=(codigo_tentado or '')[:255],
    )
    return resultado, inscricao, log
