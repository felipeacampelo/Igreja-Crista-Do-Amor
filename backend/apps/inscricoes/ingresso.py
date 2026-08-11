"""
Geração do ingresso: PDF com QR de token assinado no servidor, resolvido no
check-in (issue #10) — replica o padrão de apps/tickets/services.py do
Mio-Festa-2026 (django.core.signing + reportlab + qrcode).
"""
from io import BytesIO

import qrcode
from django.core import signing
from reportlab.lib.pagesizes import A6
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdf_canvas

from .models import Inscricao

SIGNING_SALT = 'fire-conference-ingresso'


def build_ingresso_token(inscricao):
    return signing.dumps({'inscricao_id': inscricao.id, 'token': inscricao.token}, salt=SIGNING_SALT)


def resolve_ingresso_token(token):
    payload = signing.loads(token, salt=SIGNING_SALT)
    return Inscricao.objects.get(id=payload['inscricao_id'], token=payload['token'])


def build_ingresso_pdf_bytes(inscricao):
    width, height = A6
    buffer = BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=A6)

    text_x = 10 * mm
    y = height - 15 * mm

    c.setFont('Helvetica-Bold', 16)
    c.drawString(text_x, y, 'Fire Conference')
    y -= 12 * mm

    c.setFont('Helvetica-Bold', 13)
    c.drawString(text_x, y, inscricao.nome_completo)
    y -= 8 * mm

    for label, valor in (
        ('Lote', inscricao.lote.nome),
        ('CPF', inscricao.cpf),
    ):
        c.setFont('Helvetica', 8)
        c.drawString(text_x, y, label.upper())
        c.setFont('Helvetica-Bold', 10)
        c.drawString(text_x, y - 4 * mm, valor)
        y -= 11 * mm

    qr_image = qrcode.make(build_ingresso_token(inscricao), box_size=6, border=2)
    qr_buffer = BytesIO()
    qr_image.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    qr_size = 45 * mm
    c.drawImage(ImageReader(qr_buffer), (width - qr_size) / 2, 10 * mm, width=qr_size, height=qr_size)

    c.setFont('Helvetica', 6.5)
    c.drawCentredString(width / 2, 6 * mm, 'Apresente este QR code na entrada.')

    c.showPage()
    c.save()
    return buffer.getvalue()
