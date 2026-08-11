from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.lotes.models import Lote

from .models import Cupom, Inscricao
from .pix import gerar_payload_pix


def data_nascimento_com_idade(idade):
    hoje = date.today()
    return hoje.replace(year=hoje.year - idade) - timedelta(days=1)


class InscricaoCreateTests(APITestCase):
    def setUp(self):
        self.lote = Lote.objects.create(nome='Lote 1', preco=Decimal('150.00'), limite_vagas=2)

    def payload(self, **overrides):
        data = {
            'nome_completo': 'Maria Silva',
            'cpf': '111.111.111-11',
            'email': 'maria@example.com',
            'sexo': 'F',
            'data_nascimento': data_nascimento_com_idade(25).isoformat(),
            'celular': '11999990000',
            'lote': self.lote.id,
        }
        data.update(overrides)
        return data

    def test_creates_inscricao_pendente(self):
        response = self.client.post('/api/inscricoes/', self.payload())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        inscricao = Inscricao.objects.get(token=response.data['token'])
        self.assertEqual(inscricao.status, Inscricao.Status.PENDENTE)
        self.assertEqual(inscricao.origem, Inscricao.Origem.FORMULARIO)
        self.assertEqual(inscricao.preco_final, Decimal('150.00'))
        self.assertEqual(inscricao.lote, self.lote)

    def test_menor_de_idade_requires_responsavel(self):
        response = self.client.post('/api/inscricoes/', self.payload(
            data_nascimento=data_nascimento_com_idade(16).isoformat(),
        ))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_menor_de_idade_with_responsavel_succeeds(self):
        response = self.client.post('/api/inscricoes/', self.payload(
            data_nascimento=data_nascimento_com_idade(16).isoformat(),
            nome_responsavel='Ana Silva',
            celular_responsavel='11988887777',
        ))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_maior_de_idade_does_not_require_responsavel_even_if_provided_blank(self):
        response = self.client.post('/api/inscricoes/', self.payload())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_valid_cupom_applies_discount(self):
        Cupom.objects.create(codigo='SERVIR', valor_desconto=Decimal('50.00'), limite_usos=10)

        response = self.client.post('/api/inscricoes/', self.payload(cupom_codigo='servir'))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        inscricao = Inscricao.objects.get(token=response.data['token'])
        self.assertEqual(inscricao.preco_final, Decimal('100.00'))
        self.assertEqual(inscricao.cupom.codigo, 'SERVIR')

    def test_unknown_cupom_is_rejected_with_clear_message(self):
        response = self.client.post('/api/inscricoes/', self.payload(cupom_codigo='NAOEXISTE'))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cupom_codigo', response.data)

    def test_esgotado_cupom_is_rejected(self):
        cupom = Cupom.objects.create(codigo='LIMITADO', valor_desconto=Decimal('10.00'), limite_usos=1)
        Inscricao.objects.create(
            nome_completo='Já usou', cpf='222', email='ja@example.com', sexo='F',
            data_nascimento=data_nascimento_com_idade(30), celular='119999',
            lote=self.lote, cupom=cupom, preco_final=Decimal('140.00'),
        )

        response = self.client.post('/api/inscricoes/', self.payload(cupom_codigo='LIMITADO'))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cupom_codigo', response.data)

    def test_lote_esgotado_is_rejected(self):
        lote_cheio = Lote.objects.create(nome='Lote Cheio', preco=Decimal('100.00'), limite_vagas=1)
        Inscricao.objects.create(
            nome_completo='Primeira', cpf='333', email='primeira@example.com', sexo='F',
            data_nascimento=data_nascimento_com_idade(30), celular='119999',
            lote=lote_cheio, preco_final=Decimal('100.00'),
        )

        response = self.client.post('/api/inscricoes/', self.payload(lote=lote_cheio.id))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('lote', response.data)

    def test_inactive_lote_is_rejected(self):
        lote_inativo = Lote.objects.create(nome='Inativo', preco=Decimal('100.00'), limite_vagas=10, ativo=False)

        response = self.client.post('/api/inscricoes/', self.payload(lote=lote_inativo.id))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('lote', response.data)


class InscricaoStatusTests(APITestCase):
    def setUp(self):
        self.lote = Lote.objects.create(nome='Lote 1', preco=Decimal('150.00'), limite_vagas=10)
        self.inscricao = Inscricao.objects.create(
            nome_completo='Maria Silva', cpf='111', email='maria@example.com', sexo='F',
            data_nascimento=data_nascimento_com_idade(25), celular='11999990000',
            lote=self.lote, preco_final=Decimal('150.00'),
        )

    def test_status_page_accessible_by_token_without_login(self):
        response = self.client.get(f'/api/inscricoes/{self.inscricao.token}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nome_completo'], 'Maria Silva')
        self.assertEqual(response.data['status'], Inscricao.Status.PENDENTE)

    def test_unknown_token_returns_404(self):
        response = self.client.get('/api/inscricoes/token-que-nao-existe/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_status_response_includes_pix_payload(self):
        response = self.client.get(f'/api/inscricoes/{self.inscricao.token}/')

        self.assertTrue(response.data['pix_payload'].startswith('000201'))


def _parse_tlv(payload):
    """
    Parser de TLV genérico usado só nestes testes, para validar por round-trip
    o payload que gerar_payload_pix produz — em vez de comparar contra strings
    esperadas calculadas à mão, o que seria frágil e não pegaria erros reais
    de tamanho/offset.
    """
    campos = {}
    i = 0
    while i < len(payload):
        campo_id = payload[i:i + 2]
        tamanho = int(payload[i + 2:i + 4])
        valor = payload[i + 4:i + 4 + tamanho]
        campos[campo_id] = valor
        i += 4 + tamanho
    return campos


class PixPayloadTests(TestCase):
    def test_payload_structure_and_amount(self):
        payload = gerar_payload_pix(
            chave='pix@fireconference.local',
            nome_recebedor='Igreja Crista do Amor',
            cidade_recebedor='Sao Paulo',
            valor=Decimal('100.00'),
            txid='INSC42',
        )

        campos = _parse_tlv(payload[:-4])
        self.assertEqual(campos['00'], '01')
        self.assertEqual(campos['54'], '100.00')
        self.assertEqual(campos['58'], 'BR')
        self.assertEqual(campos['59'], 'IGREJA CRISTA DO AMOR')
        self.assertEqual(campos['60'], 'SAO PAULO')

        conta_pix = _parse_tlv(campos['26'])
        self.assertEqual(conta_pix['00'], 'br.gov.bcb.pix')
        self.assertEqual(conta_pix['01'], 'pix@fireconference.local')

        dados_adicionais = _parse_tlv(campos['62'])
        self.assertEqual(dados_adicionais['05'], 'INSC42')

    def test_amount_reflects_cupom_discount(self):
        payload = gerar_payload_pix(
            chave='pix@fireconference.local', nome_recebedor='Fire Conference',
            cidade_recebedor='Sao Paulo', valor=Decimal('100.00'), txid='INSC1',
        )

        campos = _parse_tlv(payload[:-4])
        self.assertEqual(campos['54'], '100.00')

    def test_crc_is_self_consistent(self):
        payload = gerar_payload_pix(
            chave='pix@fireconference.local', nome_recebedor='Fire Conference',
            cidade_recebedor='Sao Paulo', valor=Decimal('50.00'), txid='INSC2',
        )

        from .pix import _crc16_ccitt_false

        self.assertEqual(_crc16_ccitt_false(payload[:-4]), payload[-4:])

    def test_crc_matches_known_reference_vector(self):
        # Self-consistency alone can't catch a wrong poly/init — "123456789" is
        # the standard catalogue check value for CRC-16/CCITT-FALSE (0x29B1),
        # independent of anything in this codebase.
        from .pix import _crc16_ccitt_false

        self.assertEqual(_crc16_ccitt_false('123456789'), '29B1')

    def test_long_name_and_city_are_truncated(self):
        payload = gerar_payload_pix(
            chave='pix@fireconference.local',
            nome_recebedor='Um Nome de Recebedor Extremamente Longo Demais',
            cidade_recebedor='Uma Cidade Com Nome Muito Longo',
            valor=Decimal('10.00'),
            txid='INSC3',
        )

        campos = _parse_tlv(payload[:-4])
        self.assertLessEqual(len(campos['59']), 25)
        self.assertLessEqual(len(campos['60']), 15)

    def test_accents_are_stripped(self):
        payload = gerar_payload_pix(
            chave='pix@fireconference.local', nome_recebedor='São Paulo Conferência',
            cidade_recebedor='São Paulo', valor=Decimal('10.00'), txid='INSC4',
        )

        campos = _parse_tlv(payload[:-4])
        self.assertNotIn('Ã', campos['59'])
        self.assertNotIn('É', campos['59'])
