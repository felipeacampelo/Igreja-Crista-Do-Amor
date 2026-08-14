import importlib
import os
from unittest.mock import patch

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate
from rest_framework.views import APIView

from .permissions import PodeAprovarPagamento, PodeRealizarCheckin

User = get_user_model()

# Nome do módulo começa com dígito — não dá pra usar `from .migrations.0002... import`
# (não é um identificador Python válido); carrega via importlib, igual o Django faz.
_migracao_admin_inicial = importlib.import_module('apps.users.migrations.0002_criar_admin_inicial')


class LoginTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='admin@fireconference.local', password='senha-forte-123')

    def test_admin_can_login_with_valid_credentials(self):
        response = self.client.post('/api/auth/login/', {
            'email': 'admin@fireconference.local',
            'password': 'senha-forte-123',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['token'], Token.objects.get(user=self.user).key)

    def test_login_rejects_wrong_password(self):
        response = self.client.post('/api/auth/login/', {
            'email': 'admin@fireconference.local',
            'password': 'senha-errada',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_rejects_unknown_email(self):
        response = self.client.post('/api/auth/login/', {
            'email': 'ninguem@fireconference.local',
            'password': 'senha-forte-123',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


def _protected_view(permission_class):
    """
    Minimal APIView used only by these tests to exercise the permission
    mechanism end to end. The real gated admin routes that will use
    PodeAprovarPagamento/PodeRealizarCheckin ship in #8 and #10.
    """

    class _View(APIView):
        permission_classes = [permission_class]

        def get(self, request):
            return Response({'ok': True})

    return _View.as_view()


class PermissionMechanismTests(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def _get(self, permission_class, user=None):
        request = self.factory.get('/')
        if user is not None:
            force_authenticate(request, user=user)
        return _protected_view(permission_class)(request)

    def test_anonymous_user_is_denied(self):
        response = self._get(PodeAprovarPagamento)

        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_user_without_the_permission_is_denied(self):
        user = User.objects.create_user(email='sem-permissao@fireconference.local', password='senha-forte-123')

        response = self._get(PodeAprovarPagamento, user=user)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_with_the_specific_permission_is_granted(self):
        user = User.objects.create_user(email='aprovador@fireconference.local', password='senha-forte-123')
        user.user_permissions.add(Permission.objects.get(codename='aprovar_pagamento'))

        response = self._get(PodeAprovarPagamento, user=user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_permission_is_specific_not_interchangeable(self):
        user = User.objects.create_user(email='checkin@fireconference.local', password='senha-forte-123')
        user.user_permissions.add(Permission.objects.get(codename='realizar_checkin'))

        response = self._get(PodeAprovarPagamento, user=user)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_is_granted_regardless_of_specific_permission(self):
        staff = User.objects.create_user(email='staff@fireconference.local', password='senha-forte-123', is_staff=True)

        response = self._get(PodeRealizarCheckin, user=staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CriarAdminInicialMigrationTests(TestCase):
    def _roda(self):
        _migracao_admin_inicial.criar_admin_inicial(django_apps, None)

    def test_creates_superuser_when_env_vars_are_set(self):
        with patch.dict('os.environ', {
            'DJANGO_ADMIN_EMAIL': 'admin-bootstrap@fireconference.local',
            'DJANGO_ADMIN_PASSWORD': 'senha-forte-123',
        }):
            self._roda()

        user = User.objects.get(email='admin-bootstrap@fireconference.local')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password('senha-forte-123'))

    def test_does_nothing_when_env_vars_are_missing(self):
        with patch.dict('os.environ', {}, clear=False):
            os.environ.pop('DJANGO_ADMIN_EMAIL', None)
            os.environ.pop('DJANGO_ADMIN_PASSWORD', None)
            self._roda()

        self.assertFalse(User.objects.exists())

    def test_does_not_duplicate_when_user_already_exists(self):
        User.objects.create_user(email='admin-bootstrap@fireconference.local', password='outra-senha')

        with patch.dict('os.environ', {
            'DJANGO_ADMIN_EMAIL': 'admin-bootstrap@fireconference.local',
            'DJANGO_ADMIN_PASSWORD': 'senha-forte-123',
        }):
            self._roda()

        self.assertEqual(User.objects.filter(email='admin-bootstrap@fireconference.local').count(), 1)
