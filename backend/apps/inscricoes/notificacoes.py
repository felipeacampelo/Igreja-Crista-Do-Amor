"""
Envio do ingresso por e-mail — replica o padrão de
apps/notifications/services.py do Mio-Festa-2026: usa a API do Resend via
HTTP quando configurada, senão cai no backend de e-mail padrão do Django
(console em desenvolvimento).
"""
import base64
import logging

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from .ingresso import build_ingresso_pdf_bytes

logger = logging.getLogger('apps.inscricoes')


def _enviar_email(assunto, html, destinatarios, anexos=()):
    destinatarios = [email for email in destinatarios if email]
    if not destinatarios:
        return

    if settings.RESEND_API_KEY:
        payload = {
            'from': settings.DEFAULT_FROM_EMAIL,
            'to': destinatarios,
            'subject': assunto,
            'html': html,
        }
        if anexos:
            payload['attachments'] = [
                {'filename': nome, 'content': base64.b64encode(conteudo).decode('ascii')}
                for nome, conteudo, _tipo in anexos
            ]
        response = requests.post(
            'https://api.resend.com/emails',
            headers={'Authorization': f'Bearer {settings.RESEND_API_KEY}', 'Content-Type': 'application/json'},
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        return

    mensagem = EmailMultiAlternatives(assunto, '', settings.DEFAULT_FROM_EMAIL, destinatarios)
    mensagem.attach_alternative(html, 'text/html')
    for nome, conteudo, tipo in anexos:
        mensagem.attach(nome, conteudo, tipo)
    mensagem.send(fail_silently=False)


def enviar_ingresso_email(inscricao):
    html = f"""
    <p>Olá, {inscricao.nome_completo}!</p>
    <p>Sua inscrição na Fire Conference foi confirmada. Seu ingresso está anexado a este e-mail.</p>
    <p>Lote: {inscricao.lote.nome}</p>
    """
    _enviar_email(
        'Seu ingresso — Fire Conference',
        html,
        [inscricao.email],
        anexos=[('ingresso.pdf', build_ingresso_pdf_bytes(inscricao), 'application/pdf')],
    )


def enviar_ingresso_email_seguro(inscricao):
    # A inscrição já foi confirmada antes dessa chamada — uma falha de
    # rede/timeout no envio do e-mail não pode virar um erro na aprovação,
    # que já foi bem-sucedida na prática.
    try:
        enviar_ingresso_email(inscricao)
    except Exception:
        logger.exception('Falha ao enviar e-mail de ingresso inscricao_id=%s', inscricao.id)
