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
    dados_adicionais = _campo('05', txid)

    partes = [
        _campo('00', '01'),
        _campo('01', '12'),
        _campo('26', conta_pix),
        _campo('52', '0000'),
        _campo('53', '986'),
        _campo('54', valor_formatado),
        _campo('58', 'BR'),
        _campo('59', nome),
        _campo('60', cidade),
        _campo('62', dados_adicionais),
    ]
    payload_sem_crc = ''.join(partes) + '6304'
    return payload_sem_crc + _crc16_ccitt_false(payload_sem_crc)
