# Preenche codigo_checkin para qualquer Inscricao pré-existente antes da 0007
# tornar o campo unique=True. Reimplementa a geração de código aqui (em vez de
# importar de apps.inscricoes.models) porque migrations de dados devem usar o
# modelo histórico (apps.get_model), não o modelo "atual" do app.

import secrets

from django.db import migrations

CODIGO_CHECKIN_ALFABETO = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'


def preencher_codigos_checkin(apps, schema_editor):
    Inscricao = apps.get_model('inscricoes', 'Inscricao')
    existentes = set(
        Inscricao.objects.exclude(codigo_checkin='').values_list('codigo_checkin', flat=True)
    )
    for inscricao in Inscricao.objects.filter(codigo_checkin=''):
        while True:
            codigo = ''.join(secrets.choice(CODIGO_CHECKIN_ALFABETO) for _ in range(6))
            if codigo not in existentes:
                break
        existentes.add(codigo)
        inscricao.codigo_checkin = codigo
        inscricao.save(update_fields=['codigo_checkin'])


class Migration(migrations.Migration):

    dependencies = [
        ('inscricoes', '0005_inscricao_codigo_checkin'),
    ]

    operations = [
        migrations.RunPython(preencher_codigos_checkin, migrations.RunPython.noop),
    ]
