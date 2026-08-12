# Escrita manualmente (não gerada por makemigrations): adiciona o campo sem
# unique= ainda, para não travar `migrate` numa tabela com linhas existentes
# (um AddField com unique=True precisaria de um valor default igual para
# todas as linhas pré-existentes, o que violaria a própria constraint que
# está sendo criada). A 0006 preenche cada linha com um código único e a
# 0007 só então aplica unique=True.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inscricoes', '0004_inscricao_checkin_em_inscricao_checkin_por_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='inscricao',
            name='codigo_checkin',
            field=models.CharField(blank=True, default='', editable=False, max_length=6, verbose_name='Código de check-in'),
        ),
    ]
