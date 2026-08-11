from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from .models import Lote


class LoteListTests(APITestCase):
    def test_lists_active_lote_with_vagas_restantes(self):
        Lote.objects.create(nome='Lote 1', preco=Decimal('100.00'), limite_vagas=50)

        response = self.client.get('/api/lotes/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['nome'], 'Lote 1')
        self.assertEqual(response.data[0]['preco'], '100.00')
        self.assertEqual(response.data[0]['vagas_restantes'], 50)

    def test_excludes_inactive_lote(self):
        Lote.objects.create(nome='Lote inativo', preco=Decimal('100.00'), limite_vagas=50, ativo=False)

        response = self.client.get('/api/lotes/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_excludes_sold_out_lote(self):
        Lote.objects.create(nome='Lote esgotado', preco=Decimal('100.00'), limite_vagas=0)

        response = self.client.get('/api/lotes/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])
