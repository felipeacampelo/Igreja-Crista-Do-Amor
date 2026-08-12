"""
Validação de check-in — replica o padrão de apps/checkin + apps/tickets do
Mio-Festa-2026 (resolve o token assinado do QR ou um código manual,
transiciona para "usado", bloqueia duplicado).

Diferente do Mio-Festa-2026, aqui TODA tentativa gera um CheckinAuditLog —
aceita, duplicada ou bloqueada — não só as aceitas, conforme exigido pela
spec (issue #1: "registro de cada tentativa... sucesso, duplicado, bloqueado").
"""
from django.core import signing
from django.utils import timezone

from .ingresso import resolve_ingresso_token
from .models import CheckinAuditLog, Inscricao


def checkin_via_qr(token_qr, usuario):
    try:
        inscricao = resolve_ingresso_token(token_qr)
    except (signing.BadSignature, Inscricao.DoesNotExist):
        inscricao = None
    return _processar(inscricao, usuario, token_qr)


def checkin_manual(codigo, usuario):
    inscricao = Inscricao.objects.filter(token=codigo).first()
    return _processar(inscricao, usuario, codigo)


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
