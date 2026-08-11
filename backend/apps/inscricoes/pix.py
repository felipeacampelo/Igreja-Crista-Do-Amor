"""
Geração local do payload Pix copia-e-cola (BR Code), conforme o manual de
padrões para iniciação do Pix do Banco Central — sem chamada a API bancária
ou gateway (ADR-0001).
"""
import re
import unicodedata
from decimal import Decimal


def _campo(id_campo, valor):
    return f'{id_campo}{len(valor):02d}{valor}'


def _crc16_ccitt_false(payload):
    # CRC-16/CCITT-FALSE: poly=0x1021, init=0xFFFF, sem reflexão — variante exigida pelo BR Code.
    poly = 0x1021
    crc = 0xFFFF
    for byte in payload.encode('utf-8'):
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return format(crc, '04X')


def _sanitiza(texto, tamanho_maximo):
    sem_acento = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
    limpo = re.sub(r'[^A-Za-z0-9 ]', '', sem_acento).strip().upper()
    return limpo[:tamanho_maximo]


def _sanitiza_txid(txid):
    return re.sub(r'[^A-Za-z0-9]', '', txid)[:25]


def gerar_payload_pix(chave, nome_recebedor, cidade_recebedor, valor, txid):
    nome = _sanitiza(nome_recebedor, 25)
    cidade = _sanitiza(cidade_recebedor, 15)
    txid = _sanitiza_txid(txid)
    valor_formatado = f'{Decimal(valor):.2f}'

    conta_pix = _campo('00', 'br.gov.bcb.pix') + _campo('01', chave)
    dados_adicionais = _campo('05', txid)  # subcampo 05 = txid (Reference Label)

    partes = [
        _campo('00', '01'),  # Payload Format Indicator — sempre "01"
        # Point of Initiation Method: "11" = estático/autocontido (todo o dado
        # necessário já está no payload, sem URL dinâmica) — é o nosso caso, mesmo
        # com valor e txid específicos por inscrição; "12" exigiria uma URL
        # dinâmica no campo 26 (subcampo 25), que não usamos.
        _campo('01', '11'),
        _campo('26', conta_pix),  # Merchant Account Information (GUI Pix + chave)
        _campo('52', '0000'),  # Merchant Category Code — "0000" = não informado
        _campo('53', '986'),  # Transaction Currency — 986 = BRL (ISO 4217)
        _campo('54', valor_formatado),  # Transaction Amount
        _campo('58', 'BR'),  # Country Code
        _campo('59', nome),  # Merchant Name — recebedor, máx. 25 caracteres
        _campo('60', cidade),  # Merchant City — máx. 15 caracteres
        _campo('62', dados_adicionais),  # Additional Data Field Template (txid)
    ]
    payload_sem_crc = ''.join(partes) + '6304'  # "6304" = início do campo CRC (ID 63, tamanho 04)
    return payload_sem_crc + _crc16_ccitt_false(payload_sem_crc)
