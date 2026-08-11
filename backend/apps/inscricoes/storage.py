"""
Upload de comprovantes para o Supabase Storage via API REST, usando a
service_role key (bypassa RLS) — nunca chega ao frontend.
"""
import requests
from django.conf import settings


class UploadComprovanteError(Exception):
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
