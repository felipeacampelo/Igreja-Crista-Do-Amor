"""
Geração do ingresso: PDF com QR do token da inscrição, resolvido no check-in
(issue #10) — reportlab + qrcode, inspirado em apps/tickets/services.py do
Mio-Festa-2026.

O QR carrega o próprio Inscricao.token (24 bytes aleatórios via
secrets.token_urlsafe) em vez de um payload assinado: o token já é
imprevisível e único, então assiná-lo não adiciona segurança — só uma camada
a mais para manter. O código manual impresso é um campo separado e mais
curto (Inscricao.codigo_checkin), pensado para ser digitado.
"""
from io import BytesIO

import qrcode
from reportlab.lib.pagesizes import A6
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdf_canvas


def build_ingresso_pdf_bytes(inscricao):
    width, height = A6  # cartão pequeno (~105x148mm), suficiente para um ingresso individual
    buffer = BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=A6)

    text_x = 10 * mm
    y = height - 15 * mm  # começa perto do topo, desce conforme desenha cada linha

    c.setFont('Helvetica-Bold', 16)
    c.drawString(text_x, y, 'Fire Conference')
    y -= 12 * mm

    c.setFont('Helvetica-Bold', 13)
    c.drawString(text_x, y, inscricao.nome_completo)
    y -= 8 * mm

    # Cada label ocupa uma linha pequena acima do valor em negrito, formando um bloco de ~11mm.
    for label, valor in (
        ('Lote', inscricao.lote.nome),
        ('CPF', inscricao.cpf),
        ('Celular', inscricao.celular),
    ):
        c.setFont('Helvetica', 8)
        c.drawString(text_x, y, label.upper())
        c.setFont('Helvetica-Bold', 10)
        c.drawString(text_x, y - 4 * mm, valor)
        y -= 11 * mm

    # Código manual de fallback: curto (6 caracteres, sem 0/O/1/I/L) para dar
    # para digitar de cabeça no check-in caso a câmera falhe — diferente do
    # Inscricao.token (longo, usado na URL da página de status e no QR).
    c.setFont('Helvetica', 7)
    c.drawCentredString(width / 2, 72 * mm, 'Código manual de check-in')
    c.setFont('Helvetica-Bold', 18)
    c.drawCentredString(width / 2, 63 * mm, inscricao.codigo_checkin)

    qr_image = qrcode.make(inscricao.token, box_size=6, border=2)
    qr_buffer = BytesIO()
    qr_image.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    qr_size = 45 * mm
    c.drawImage(ImageReader(qr_buffer), (width - qr_size) / 2, 14 * mm, width=qr_size, height=qr_size)  # centralizado

    c.setFont('Helvetica', 6.5)
    c.drawCentredString(width / 2, 8 * mm, 'Apresente este QR code na entrada.')

    c.showPage()
    c.save()
    return buffer.getvalue()
