from datetime import date, timedelta
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.lotes.models import Lote

from .models import Cupom, Inscricao


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
