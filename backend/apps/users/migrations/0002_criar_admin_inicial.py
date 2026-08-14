from decouple import config
from django.db import migrations


def criar_admin_inicial(apps, schema_editor):
    email = config('DJANGO_ADMIN_EMAIL', default='')
    password = config('DJANGO_ADMIN_PASSWORD', default='')
    if not email or not password:
        return

    User = apps.get_model('users', 'User')
    if User.objects.filter(email__iexact=email).exists():
        return

    # apps.get_model() devolve um modelo histórico sem o UserManager custom
    # (create_superuser/set_password) — cria direto e faz o hash da senha
    # com o hasher configurado no Django (mesmo caminho que set_password usa).
    from django.contrib.auth.hashers import make_password

    User.objects.create(
        email=email,
        password=make_password(password),
        is_staff=True,
        is_superuser=True,
        is_active=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(criar_admin_inicial, migrations.RunPython.noop),
    ]
