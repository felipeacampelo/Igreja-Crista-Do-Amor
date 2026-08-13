import tempfile
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.lotes.models import Lote

from .importacao import importar_linhas
from .models import CheckinAuditLog, Cupom, Inscricao
from .pix import gerar_payload_pix
from .storage import UploadComprovanteError

User = get_user_model()


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
        self.assertEqual(len(inscricao.codigo_checkin), 6)
        self.assertTrue(set(inscricao.codigo_checkin) <= set('ABCDEFGHJKMNPQRSTUVWXYZ23456789'))

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


class CodigoCheckinGeracaoTests(TestCase):
    def setUp(self):
        self.lote = Lote.objects.create(nome='Lote 1', preco=Decimal('150.00'), limite_vagas=10)

    def _cria_inscricao(self, **overrides):
        dados = dict(
            nome_completo='Maria Silva', cpf='111', email='maria@example.com', sexo='F',
            data_nascimento=data_nascimento_com_idade(25), celular='11999990000',
            lote=self.lote, preco_final=Decimal('150.00'),
        )
        dados.update(overrides)
        return Inscricao.objects.create(**dados)

    def test_distinct_inscricoes_get_distinct_codigo_checkin(self):
        primeira = self._cria_inscricao(email='um@example.com')
        segunda = self._cria_inscricao(email='dois@example.com')

        self.assertNotEqual(primeira.codigo_checkin, segunda.codigo_checkin)

    def test_generation_retries_on_collision(self):
        existente = self._cria_inscricao(email='primeira@example.com')

        # Força o primeiro sorteio a repetir o código já existente; o segundo
        # sorteio usa uma letra diferente pra garantir que o retry funcionou.
        colidido = list(existente.codigo_checkin)
        alternativo = 'A' if colidido[0] != 'A' else 'B'

        with patch('apps.inscricoes.models.secrets.choice') as mock_choice:
            mock_choice.side_effect = colidido + [alternativo] * 6
            nova = self._cria_inscricao(email='segunda@example.com')

        self.assertNotEqual(nova.codigo_checkin, existente.codigo_checkin)
        self.assertTrue(mock_choice.call_count > 6)  # precisou de mais de uma tentativa


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

    def test_status_response_includes_codigo_checkin(self):
        response = self.client.get(f'/api/inscricoes/{self.inscricao.token}/')

        self.assertEqual(response.data['codigo_checkin'], self.inscricao.codigo_checkin)


class ComprovanteUploadTests(APITestCase):
    def setUp(self):
        self.lote = Lote.objects.create(nome='Lote 1', preco=Decimal('150.00'), limite_vagas=10)
        self.inscricao = Inscricao.objects.create(
            nome_completo='Maria Silva', cpf='111', email='maria@example.com', sexo='F',
            data_nascimento=data_nascimento_com_idade(25), celular='11999990000',
            lote=self.lote, preco_final=Decimal('150.00'),
        )

    def _arquivo(self, nome='comprovante.png', tipo='image/png', conteudo=b'fake-image-bytes'):
        return SimpleUploadedFile(nome, conteudo, content_type=tipo)

    @patch('apps.inscricoes.views.upload_comprovante')
    def test_upload_transitions_status_and_stores_path(self, mock_upload):
        mock_upload.return_value = 'caminho/fake.png'

        response = self.client.post(
            f'/api/inscricoes/{self.inscricao.token}/comprovante/',
            {'arquivo': self._arquivo()},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Inscricao.Status.COMPROVANTE_ENVIADO)
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.status, Inscricao.Status.COMPROVANTE_ENVIADO)
        self.assertTrue(self.inscricao.comprovante_path)
        mock_upload.assert_called_once()

    @patch('apps.inscricoes.views.upload_comprovante')
    def test_accepts_pdf(self, mock_upload):
        response = self.client.post(
            f'/api/inscricoes/{self.inscricao.token}/comprovante/',
            {'arquivo': self._arquivo(nome='comprovante.pdf', tipo='application/pdf')},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('apps.inscricoes.views.upload_comprovante')
    def test_rejects_disallowed_file_type(self, mock_upload):
        response = self.client.post(
            f'/api/inscricoes/{self.inscricao.token}/comprovante/',
            {'arquivo': self._arquivo(nome='comprovante.txt', tipo='text/plain')},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_upload.assert_not_called()
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.status, Inscricao.Status.PENDENTE)

    @patch('apps.inscricoes.views.upload_comprovante')
    def test_rejects_file_too_large(self, mock_upload):
        arquivo_grande = self._arquivo(conteudo=b'x' * (10 * 1024 * 1024 + 1))

        response = self.client.post(
            f'/api/inscricoes/{self.inscricao.token}/comprovante/',
            {'arquivo': arquivo_grande},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_upload.assert_not_called()

    @patch('apps.inscricoes.views.upload_comprovante')
    def test_rejects_upload_when_not_pendente(self, mock_upload):
        self.inscricao.status = Inscricao.Status.CONFIRMADA
        self.inscricao.save()

        response = self.client.post(
            f'/api/inscricoes/{self.inscricao.token}/comprovante/',
            {'arquivo': self._arquivo()},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_upload.assert_not_called()

    @patch('apps.inscricoes.views.upload_comprovante')
    def test_storage_failure_does_not_change_status(self, mock_upload):
        mock_upload.side_effect = UploadComprovanteError('boom')

        response = self.client.post(
            f'/api/inscricoes/{self.inscricao.token}/comprovante/',
            {'arquivo': self._arquivo()},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.status, Inscricao.Status.PENDENTE)
        self.assertEqual(self.inscricao.comprovante_path, '')

    def test_upload_to_unknown_token_returns_404(self):
        response = self.client.post(
            '/api/inscricoes/token-que-nao-existe/comprovante/',
            {'arquivo': self._arquivo()},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


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


class AprovacaoPagamentoTests(APITestCase):
    def setUp(self):
        self.lote = Lote.objects.create(nome='Lote 1', preco=Decimal('150.00'), limite_vagas=10)
        self.inscricao = Inscricao.objects.create(
            nome_completo='Maria Silva', cpf='111', email='maria@example.com', sexo='F',
            data_nascimento=data_nascimento_com_idade(25), celular='11999990000',
            lote=self.lote, preco_final=Decimal('150.00'), status=Inscricao.Status.COMPROVANTE_ENVIADO,
            comprovante_path='some-token/comprovante.png',
        )

        self.aprovador = User.objects.create_user(email='aprovador@fireconference.local', password='senha-forte-123')
        self.aprovador.user_permissions.add(Permission.objects.get(codename='aprovar_pagamento'))

        self.sem_permissao = User.objects.create_user(email='sem-permissao@fireconference.local', password='senha-forte-123')

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    @patch('apps.inscricoes.serializers.gerar_url_assinada')
    def test_real_login_token_grants_queue_access_end_to_end(self, mock_url):
        # force_authenticate (used elsewhere in this class) proves the permission
        # class works, but skips real token auth — this proves a token obtained
        # from the actual login endpoint (#4) actually works against this route.
        # The Supabase call itself is mocked here too — already covered separately.
        mock_url.return_value = 'https://signed.example.com/comprovante.png'

        login_response = self.client.post('/api/auth/login/', {
            'email': 'aprovador@fireconference.local',
            'password': 'senha-forte-123',
        })
        token = login_response.data['token']

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        response = self.client.get('/api/admin/inscricoes/fila-aprovacao/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('apps.inscricoes.serializers.gerar_url_assinada')
    def test_aprovador_sees_queue_with_comprovante_url(self, mock_url):
        mock_url.return_value = 'https://signed.example.com/comprovante.png'
        self._auth(self.aprovador)

        response = self.client.get('/api/admin/inscricoes/fila-aprovacao/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['nome_completo'], 'Maria Silva')
        self.assertEqual(response.data[0]['preco_final'], '150.00')
        self.assertEqual(response.data[0]['comprovante_url'], 'https://signed.example.com/comprovante.png')

    def test_queue_excludes_other_statuses(self):
        Inscricao.objects.create(
            nome_completo='Pendente', cpf='222', email='pendente@example.com', sexo='F',
            data_nascimento=data_nascimento_com_idade(25), celular='119999',
            lote=self.lote, preco_final=Decimal('150.00'), status=Inscricao.Status.PENDENTE,
        )
        self._auth(self.aprovador)

        response = self.client.get('/api/admin/inscricoes/fila-aprovacao/')

        self.assertEqual(len(response.data), 1)

    def test_user_without_permission_cannot_see_queue(self):
        self._auth(self.sem_permissao)

        response = self.client.get('/api/admin/inscricoes/fila-aprovacao/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_see_queue(self):
        response = self.client.get('/api/admin/inscricoes/fila-aprovacao/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_aprovador_can_approve(self):
        self._auth(self.aprovador)

        response = self.client.post(f'/api/admin/inscricoes/{self.inscricao.id}/aprovar/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.status, Inscricao.Status.CONFIRMADA)

    def test_aprovador_can_reject_with_reason(self):
        self._auth(self.aprovador)

        response = self.client.post(
            f'/api/admin/inscricoes/{self.inscricao.id}/rejeitar/',
            {'motivo': 'Comprovante ilegível'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.status, Inscricao.Status.REJEITADA)
        self.assertEqual(self.inscricao.motivo_rejeicao, 'Comprovante ilegível')

    def test_rejection_reason_is_required(self):
        self._auth(self.aprovador)

        response = self.client.post(f'/api/admin/inscricoes/{self.inscricao.id}/rejeitar/', {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejection_reason_visible_on_public_status_page(self):
        self._auth(self.aprovador)
        self.client.post(
            f'/api/admin/inscricoes/{self.inscricao.id}/rejeitar/',
            {'motivo': 'Valor incorreto'},
        )

        response = self.client.get(f'/api/inscricoes/{self.inscricao.token}/')

        self.assertEqual(response.data['status'], Inscricao.Status.REJEITADA)
        self.assertEqual(response.data['motivo_rejeicao'], 'Valor incorreto')

    def test_user_without_permission_cannot_approve(self):
        self._auth(self.sem_permissao)

        response = self.client.post(f'/api/admin/inscricoes/{self.inscricao.id}/aprovar/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.status, Inscricao.Status.COMPROVANTE_ENVIADO)

    def test_cannot_approve_inscricao_not_in_review_queue(self):
        self.inscricao.status = Inscricao.Status.PENDENTE
        self.inscricao.save()
        self._auth(self.aprovador)

        response = self.client.post(f'/api/admin/inscricoes/{self.inscricao.id}/aprovar/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approving_sends_ingresso_email_with_pdf_attachment(self):
        self._auth(self.aprovador)

        self.client.post(f'/api/admin/inscricoes/{self.inscricao.id}/aprovar/')

        self.assertEqual(len(mail.outbox), 1)
        enviado = mail.outbox[0]
        self.assertEqual(enviado.to, ['maria@example.com'])
        self.assertEqual(len(enviado.attachments), 1)
        nome, conteudo, tipo = enviado.attachments[0]
        self.assertEqual(nome, 'ingresso.pdf')
        self.assertEqual(tipo, 'application/pdf')
        self.assertTrue(conteudo.startswith(b'%PDF'))

    def test_rejecting_does_not_send_ingresso_email(self):
        self._auth(self.aprovador)

        self.client.post(f'/api/admin/inscricoes/{self.inscricao.id}/rejeitar/', {'motivo': 'teste'})

        self.assertEqual(len(mail.outbox), 0)


class IngressoTests(APITestCase):
    def setUp(self):
        self.lote = Lote.objects.create(nome='Lote 1', preco=Decimal('150.00'), limite_vagas=10)
        self.inscricao = Inscricao.objects.create(
            nome_completo='Maria Silva', cpf='111', email='maria@example.com', sexo='F',
            data_nascimento=data_nascimento_com_idade(25), celular='11999990000',
            lote=self.lote, preco_final=Decimal('150.00'), status=Inscricao.Status.CONFIRMADA,
        )

    def test_download_returns_pdf_when_confirmada(self):
        response = self.client.get(f'/api/inscricoes/{self.inscricao.token}/ingresso/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_download_not_available_when_not_confirmada(self):
        self.inscricao.status = Inscricao.Status.PENDENTE
        self.inscricao.save()

        response = self.client.get(f'/api/inscricoes/{self.inscricao.token}/ingresso/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_download_unknown_token_returns_404(self):
        response = self.client.get('/api/inscricoes/token-que-nao-existe/ingresso/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PixQrCodeTests(APITestCase):
    def setUp(self):
        self.lote = Lote.objects.create(nome='Lote 1', preco=Decimal('150.00'), limite_vagas=10)
        self.inscricao = Inscricao.objects.create(
            nome_completo='Maria Silva', cpf='111', email='maria@example.com', sexo='F',
            data_nascimento=data_nascimento_com_idade(25), celular='11999990000',
            lote=self.lote, preco_final=Decimal('150.00'),
        )

    def test_returns_png_image(self):
        response = self.client.get(f'/api/inscricoes/{self.inscricao.token}/pix-qr/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertTrue(response.content.startswith(b'\x89PNG'))

    def test_available_regardless_of_status(self):
        # O QR do Pix precisa aparecer justamente enquanto a inscrição ainda não
        # está confirmada — é o que falta pra chegar lá.
        for novo_status in (Inscricao.Status.PENDENTE, Inscricao.Status.COMPROVANTE_ENVIADO, Inscricao.Status.CONFIRMADA):
            self.inscricao.status = novo_status
            self.inscricao.save()

            response = self.client.get(f'/api/inscricoes/{self.inscricao.token}/pix-qr/')

            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unknown_token_returns_404(self):
        response = self.client.get('/api/inscricoes/token-que-nao-existe/pix-qr/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_qr_encodes_the_same_payload_as_the_status_endpoint(self):
        import io

        import qrcode

        status_response = self.client.get(f'/api/inscricoes/{self.inscricao.token}/')
        qr_response = self.client.get(f'/api/inscricoes/{self.inscricao.token}/pix-qr/')

        # Sem lib de leitura de QR nas dependências: em vez de decodificar a
        # imagem retornada, gera de novo a partir do mesmo payload (mesmos
        # parâmetros da view) e compara os bytes do PNG.
        esperado = qrcode.make(status_response.data['pix_payload'], box_size=6, border=2)
        buffer_esperado = io.BytesIO()
        esperado.save(buffer_esperado, format='PNG')

        self.assertEqual(qr_response.content, buffer_esperado.getvalue())


class CheckinTests(APITestCase):
    def setUp(self):
        self.lote = Lote.objects.create(nome='Lote 1', preco=Decimal('150.00'), limite_vagas=10)
        self.inscricao = Inscricao.objects.create(
            nome_completo='Maria Silva', cpf='111', email='maria@example.com', sexo='F',
            data_nascimento=data_nascimento_com_idade(25), celular='11999990000',
            lote=self.lote, preco_final=Decimal('150.00'), status=Inscricao.Status.CONFIRMADA,
        )

        self.checkin_staff = User.objects.create_user(email='checkin@fireconference.local', password='senha-forte-123')
        self.checkin_staff.user_permissions.add(Permission.objects.get(codename='realizar_checkin'))

        self.sem_permissao = User.objects.create_user(email='sem-permissao-checkin@fireconference.local', password='senha-forte-123')

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def test_manual_checkin_aceita_valid_unused_ingresso(self):
        self._auth(self.checkin_staff)

        response = self.client.post('/api/admin/checkin/manual/', {'codigo': self.inscricao.codigo_checkin})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resultado'], 'aceita')
        self.assertEqual(response.data['nome_completo'], 'Maria Silva')
        self.inscricao.refresh_from_db()
        self.assertIsNotNone(self.inscricao.checkin_em)
        self.assertEqual(self.inscricao.checkin_por, self.checkin_staff)

    def test_manual_checkin_duplicada_on_second_attempt(self):
        self._auth(self.checkin_staff)
        self.client.post('/api/admin/checkin/manual/', {'codigo': self.inscricao.codigo_checkin})

        response = self.client.post('/api/admin/checkin/manual/', {'codigo': self.inscricao.codigo_checkin})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resultado'], 'duplicada')

    def test_manual_checkin_bloqueada_for_unconfirmed_inscricao(self):
        self.inscricao.status = Inscricao.Status.PENDENTE
        self.inscricao.save()
        self._auth(self.checkin_staff)

        response = self.client.post('/api/admin/checkin/manual/', {'codigo': self.inscricao.codigo_checkin})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resultado'], 'bloqueada')
        self.inscricao.refresh_from_db()
        self.assertIsNone(self.inscricao.checkin_em)

    def test_manual_checkin_bloqueada_for_unknown_code(self):
        self._auth(self.checkin_staff)

        response = self.client.post('/api/admin/checkin/manual/', {'codigo': 'codigo-que-nao-existe'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resultado'], 'bloqueada')
        self.assertIsNone(response.data['nome_completo'])

    def test_manual_checkin_accepts_lowercase_and_surrounding_whitespace(self):
        self._auth(self.checkin_staff)

        response = self.client.post('/api/admin/checkin/manual/', {'codigo': f'  {self.inscricao.codigo_checkin.lower()}  '})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resultado'], 'aceita')

    def test_scan_checkin_aceita_valid_qr_token(self):
        self._auth(self.checkin_staff)

        response = self.client.post('/api/admin/checkin/scan/', {'token_qr': self.inscricao.token})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resultado'], 'aceita')

    def test_scan_checkin_bloqueada_for_unknown_qr_token(self):
        self._auth(self.checkin_staff)

        response = self.client.post('/api/admin/checkin/scan/', {'token_qr': 'codigo-que-nao-existe'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resultado'], 'bloqueada')

    def test_every_attempt_is_logged_including_blocked_and_duplicate(self):
        self._auth(self.checkin_staff)

        self.client.post('/api/admin/checkin/manual/', {'codigo': self.inscricao.codigo_checkin})  # aceita
        self.client.post('/api/admin/checkin/manual/', {'codigo': self.inscricao.codigo_checkin})  # duplicada
        self.client.post('/api/admin/checkin/manual/', {'codigo': 'inexistente'})  # bloqueada

        logs = CheckinAuditLog.objects.order_by('criado_em')
        self.assertEqual(logs.count(), 3)
        self.assertEqual(list(logs.values_list('resultado', flat=True)), ['aceita', 'duplicada', 'bloqueada'])
        self.assertTrue(all(log.usuario == self.checkin_staff for log in logs))

    def test_user_without_permission_cannot_checkin(self):
        self._auth(self.sem_permissao)

        response = self.client.post('/api/admin/checkin/manual/', {'codigo': self.inscricao.codigo_checkin})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.inscricao.refresh_from_db()
        self.assertIsNone(self.inscricao.checkin_em)

    def test_anonymous_cannot_checkin(self):
        response = self.client.post('/api/admin/checkin/manual/', {'codigo': self.inscricao.codigo_checkin})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ImportacaoPlanilhaTests(TestCase):
    def setUp(self):
        self.lote = Lote.objects.create(nome='Lote 1', preco=Decimal('150.00'), limite_vagas=2)

    def _linha(self, **overrides):
        linha = {
            'nome_completo': 'Maria Silva',
            'cpf': '111.111.111-11',
            'email': 'maria@example.com',
            'sexo': 'F',
            'data_nascimento': data_nascimento_com_idade(25).isoformat(),
            'celular': '11999990000',
            'nome_responsavel': '',
            'celular_responsavel': '',
            'lote': self.lote.nome,
            'cupom_codigo': '',
        }
        linha.update(overrides)
        return linha

    def test_valid_row_creates_confirmed_imported_inscricao(self):
        resultado = importar_linhas([self._linha()])

        self.assertEqual(resultado.importadas, 1)
        self.assertEqual(resultado.puladas, 0)
        self.assertEqual(resultado.com_erro, 0)

        inscricao = Inscricao.objects.get(cpf='111.111.111-11')
        self.assertEqual(inscricao.nome_completo, 'Maria Silva')
        self.assertEqual(inscricao.status, Inscricao.Status.CONFIRMADA)
        self.assertEqual(inscricao.origem, Inscricao.Origem.IMPORTACAO)
        self.assertEqual(inscricao.lote, self.lote)
        self.assertEqual(inscricao.preco_final, Decimal('150.00'))

    def test_imported_inscricao_counts_toward_lote_vagas(self):
        importar_linhas([
            self._linha(cpf='111', email='um@example.com'),
            self._linha(cpf='222', email='dois@example.com'),
        ])

        self.assertEqual(self.lote.vagas_ocupadas, 2)
        self.assertTrue(self.lote.esgotado)

    def test_row_beyond_lote_limit_is_reported_as_error_not_created(self):
        resultado = importar_linhas([
            self._linha(cpf='111', email='um@example.com'),
            self._linha(cpf='222', email='dois@example.com'),
            self._linha(cpf='333', email='tres@example.com'),  # limite_vagas=2
        ])

        self.assertEqual(resultado.importadas, 2)
        self.assertEqual(resultado.com_erro, 1)
        self.assertFalse(Inscricao.objects.filter(cpf='333').exists())

    def test_reimporting_same_file_is_idempotent(self):
        linha = self._linha()

        primeira = importar_linhas([linha])
        segunda = importar_linhas([linha])

        self.assertEqual(primeira.importadas, 1)
        self.assertEqual(segunda.importadas, 0)
        self.assertEqual(segunda.puladas, 1)
        self.assertEqual(Inscricao.objects.filter(cpf='111.111.111-11').count(), 1)

    def test_cpf_matching_existing_non_imported_inscricao_is_skipped_not_duplicated(self):
        Inscricao.objects.create(
            nome_completo='Maria Silva', cpf='111.111.111-11', email='maria@example.com', sexo='F',
            data_nascimento=data_nascimento_com_idade(25), celular='11999990000',
            lote=self.lote, preco_final=Decimal('150.00'), origem=Inscricao.Origem.FORMULARIO,
        )

        resultado = importar_linhas([self._linha()])

        self.assertEqual(resultado.puladas, 1)
        self.assertEqual(Inscricao.objects.filter(cpf='111.111.111-11').count(), 1)
        self.assertIn('Formulário', resultado.mensagens[0][2])

    def test_row_that_fails_to_save_does_not_abort_remaining_rows(self):
        with patch(
            'apps.inscricoes.importacao.InscricaoCreateSerializer.create',
            side_effect=[Exception('falha simulada'), Inscricao(id=999)],
        ):
            # A própria mock acima não persiste de verdade; testamos só que a
            # segunda linha ainda é tentada (não haveria 2ª chamada se a 1ª
            # exceção tivesse propagado e derrubado o loop inteiro).
            with patch('apps.inscricoes.importacao.enviar_ingresso_email_seguro'):
                resultado = importar_linhas([
                    self._linha(cpf='111', email='um@example.com'),
                    self._linha(cpf='222', email='dois@example.com'),
                ])

        self.assertEqual(resultado.com_erro, 1)
        self.assertEqual(resultado.importadas, 1)

    def test_unknown_lote_is_reported_as_error(self):
        resultado = importar_linhas([self._linha(lote='Lote Que Não Existe')])

        self.assertEqual(resultado.com_erro, 1)
        self.assertEqual(resultado.importadas, 0)
        self.assertFalse(Inscricao.objects.filter(cpf='111.111.111-11').exists())

    def test_menor_de_idade_sem_responsavel_is_reported_as_error(self):
        resultado = importar_linhas([self._linha(
            data_nascimento=data_nascimento_com_idade(16).isoformat(),
        )])

        self.assertEqual(resultado.com_erro, 1)
        self.assertFalse(Inscricao.objects.filter(cpf='111.111.111-11').exists())

    def test_cupom_codigo_applies_discount(self):
        Cupom.objects.create(codigo='SERVIR', valor_desconto=Decimal('50.00'), limite_usos=10)

        importar_linhas([self._linha(cupom_codigo='servir')])

        inscricao = Inscricao.objects.get(cpf='111.111.111-11')
        self.assertEqual(inscricao.preco_final, Decimal('100.00'))
        self.assertEqual(inscricao.cupom.codigo, 'SERVIR')

    def test_import_sends_ingresso_email(self):
        importar_linhas([self._linha()])

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['maria@example.com'])
        self.assertEqual(len(mail.outbox[0].attachments), 1)

    def test_dry_run_does_not_create_or_send_email(self):
        resultado = importar_linhas([self._linha()], dry_run=True)

        self.assertEqual(resultado.importadas, 1)
        self.assertFalse(Inscricao.objects.filter(cpf='111.111.111-11').exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_dry_run_accounts_for_lote_capacity_used_by_earlier_rows_in_same_batch(self):
        # limite_vagas=2: como nada é gravado num dry-run, lote.esgotado (calculado
        # do banco) não veria essas linhas sozinho — sem o contador em memória, as
        # 3 linhas passariam como válidas mesmo violando o limite do lote.
        resultado = importar_linhas([
            self._linha(cpf='111', email='um@example.com'),
            self._linha(cpf='222', email='dois@example.com'),
            self._linha(cpf='333', email='tres@example.com'),
        ], dry_run=True)

        self.assertEqual(resultado.importadas, 2)
        self.assertEqual(resultado.com_erro, 1)
        self.assertEqual(Inscricao.objects.count(), 0)  # dry-run: nada foi gravado

    def test_dry_run_accounts_for_cupom_limit_used_by_earlier_rows_in_same_batch(self):
        Cupom.objects.create(codigo='SERVIR', valor_desconto=Decimal('50.00'), limite_usos=1)

        resultado = importar_linhas([
            self._linha(cpf='111', email='um@example.com', cupom_codigo='servir'),
            self._linha(cpf='222', email='dois@example.com', cupom_codigo='servir'),
        ], dry_run=True)

        self.assertEqual(resultado.importadas, 1)
        self.assertEqual(resultado.com_erro, 1)

    def test_management_command_reads_csv_file_end_to_end(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as arquivo:
            arquivo.write(
                'nome_completo,cpf,email,sexo,data_nascimento,celular,nome_responsavel,'
                'celular_responsavel,lote,cupom_codigo\n'
            )
            arquivo.write(
                f'Maria Silva,111.111.111-11,maria@example.com,F,'
                f'{data_nascimento_com_idade(25).isoformat()},11999990000,,,{self.lote.nome},\n'
            )
            caminho = arquivo.name

        call_command('importar_planilha', file=caminho)

        self.assertTrue(Inscricao.objects.filter(cpf='111.111.111-11').exists())
