# Escrita manualmente, na sequência de 0005+0006 (adiciona a coluna, depois
# preenche as linhas existentes) — só agora é seguro aplicar unique=True.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inscricoes', '0006_inscricao_codigo_checkin_backfill'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inscricao',
            name='codigo_checkin',
            field=models.CharField(editable=False, max_length=6, unique=True, verbose_name='Código de check-in'),
        ),
    ]
