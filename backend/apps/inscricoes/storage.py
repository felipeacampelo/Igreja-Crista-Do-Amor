"""
Upload e leitura de comprovantes no Supabase Storage via API REST, usando a
service_role key (bypassa RLS) — nunca chega ao frontend.
"""
import requests
from django.conf import settings


class UploadComprovanteError(Exception):
    pass


class AssinaturaUrlError(Exception):
    pass


def upload_comprovante(caminho, arquivo):
    url = (
        f'{settings.SUPABASE_URL}/storage/v1/object/'
        f'{settings.SUPABASE_COMPROVANTES_BUCKET}/{caminho}'
    )
    headers = {
        'Authorization': f'Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}',
        'Content-Type': arquivo.content_type,
        'x-upsert': 'true',
    }

    try:
        response = requests.post(url, headers=headers, data=arquivo.read(), timeout=30)
    except requests.RequestException as exc:
        raise UploadComprovanteError(str(exc)) from exc

    if response.status_code >= 400:
        raise UploadComprovanteError(
            f'Supabase Storage retornou {response.status_code}: {response.text[:500]}'
        )

    return caminho


def gerar_url_assinada(caminho, expira_em=3600):
    """URL temporária para o aprovador visualizar um comprovante do bucket privado."""
    url = (
        f'{settings.SUPABASE_URL}/storage/v1/object/sign/'
        f'{settings.SUPABASE_COMPROVANTES_BUCKET}/{caminho}'
    )
    headers = {'Authorization': f'Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}'}

    try:
        response = requests.post(url, headers=headers, json={'expiresIn': expira_em}, timeout=30)
    except requests.RequestException as exc:
        raise AssinaturaUrlError(str(exc)) from exc

    if response.status_code >= 400:
        raise AssinaturaUrlError(
            f'Supabase Storage retornou {response.status_code}: {response.text[:500]}'
        )

    signed_url = response.json().get('signedURL')
    if not signed_url:
        raise AssinaturaUrlError('Resposta do Supabase Storage sem signedURL.')

    return f'{settings.SUPABASE_URL}/storage/v1{signed_url}'
