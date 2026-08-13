from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Lote

User = get_user_model()


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


class LoteAdminApiTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            email='staff@fireconference.local', password='senha-forte-123', is_staff=True,
        )
        self.sem_permissao = User.objects.create_user(email='sem-permissao@fireconference.local', password='senha-forte-123')

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def test_list_includes_inactive_and_sold_out_lotes(self):
        Lote.objects.create(nome='Ativo', preco=Decimal('100.00'), limite_vagas=50)
        Lote.objects.create(nome='Inativo', preco=Decimal('120.00'), limite_vagas=50, ativo=False)
        Lote.objects.create(nome='Esgotado', preco=Decimal('140.00'), limite_vagas=0, ativo=False)
        self._auth(self.staff)

        response = self.client.get('/api/admin/lotes/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_create_lote(self):
        self._auth(self.staff)

        response = self.client.post('/api/admin/lotes/', {
            'nome': 'Lote Novo', 'preco': '200.00', 'limite_vagas': 100, 'ativo': True,
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Lote.objects.filter(nome='Lote Novo').exists())

    def test_activating_a_lote_via_patch_deactivates_the_previous_one(self):
        primeiro = Lote.objects.create(nome='Lote 1', preco=Decimal('100.00'), limite_vagas=50)
        segundo = Lote.objects.create(nome='Lote 2', preco=Decimal('150.00'), limite_vagas=50, ativo=False)
        self._auth(self.staff)

        response = self.client.patch(f'/api/admin/lotes/{segundo.id}/', {'ativo': True})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        primeiro.refresh_from_db()
        self.assertFalse(primeiro.ativo)

    def test_non_staff_user_cannot_manage_lotes(self):
        self._auth(self.sem_permissao)

        response = self.client.get('/api/admin/lotes/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_manage_lotes(self):
        response = self.client.get('/api/admin/lotes/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
