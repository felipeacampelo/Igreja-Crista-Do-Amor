from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from .models import Lote


class LoteAtivoTests(APITestCase):
    def test_returns_active_lote_with_vagas_restantes(self):
        Lote.objects.create(nome='Lote 1', preco=Decimal('100.00'), limite_vagas=50)

        response = self.client.get('/api/lotes/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nome'], 'Lote 1')
        self.assertEqual(response.data['preco'], '100.00')
        self.assertEqual(response.data['vagas_restantes'], 50)

    def test_returns_null_when_no_active_lote(self):
        Lote.objects.create(nome='Lote inativo', preco=Decimal('100.00'), limite_vagas=50, ativo=False)

        response = self.client.get('/api/lotes/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data)

    def test_returns_null_when_active_lote_is_sold_out(self):
        Lote.objects.create(nome='Lote esgotado', preco=Decimal('100.00'), limite_vagas=0)

        response = self.client.get('/api/lotes/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data)


class LoteAtivoUnicoTests(APITestCase):
    def test_activating_a_lote_deactivates_the_previous_active_one(self):
        primeiro = Lote.objects.create(nome='Lote 1', preco=Decimal('100.00'), limite_vagas=50)
        segundo = Lote.objects.create(nome='Lote 2', preco=Decimal('150.00'), limite_vagas=50)

        primeiro.refresh_from_db()
        self.assertFalse(primeiro.ativo)
        self.assertTrue(segundo.ativo)

    def test_api_reflects_only_the_current_active_lote(self):
        Lote.objects.create(nome='Lote 1', preco=Decimal('100.00'), limite_vagas=50)
        Lote.objects.create(nome='Lote 2', preco=Decimal('150.00'), limite_vagas=50)

        response = self.client.get('/api/lotes/')

        self.assertEqual(response.data['nome'], 'Lote 2')

    def test_deactivating_a_lote_does_not_activate_others(self):
        primeiro = Lote.objects.create(nome='Lote 1', preco=Decimal('100.00'), limite_vagas=50)
        Lote.objects.create(nome='Lote 2', preco=Decimal('150.00'), limite_vagas=50, ativo=False)

        primeiro.ativo = False
        primeiro.save()

        response = self.client.get('/api/lotes/')

        self.assertIsNone(response.data)
