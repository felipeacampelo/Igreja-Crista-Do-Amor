"""
Script pontual (issue #11): importa inscrições confirmadas da planilha usada
antes desse sistema existir. Não é feature de admin/UI — roda uma única vez
via linha de comando.

Formato esperado do CSV (cabeçalho na primeira linha), colunas:
    nome_completo,cpf,email,sexo,data_nascimento,celular,nome_responsavel,celular_responsavel,lote,cupom_codigo

- sexo: M ou F
- data_nascimento: AAAA-MM-DD
- nome_responsavel/celular_responsavel: obrigatórios se menor de idade, em branco caso contrário
- lote: nome do Lote já cadastrado no sistema (precisa bater exatamente, sem diferenciar maiúsculas/minúsculas)
- cupom_codigo: opcional, em branco se não houve cupom

Uso:
    python manage.py importar_planilha --file caminho/planilha.csv
    python manage.py importar_planilha --file caminho/planilha.csv --dry-run
"""
import csv

from django.core.management.base import BaseCommand, CommandError

from apps.inscricoes.importacao import importar_linhas

ESTILO_POR_TIPO = {'ok': 'SUCCESS', 'pulada': 'WARNING', 'erro': 'ERROR'}


class Command(BaseCommand):
    help = (
        'Importa inscrições confirmadas da planilha antiga (issue #11) — script pontual, '
        'não é feature reaproveitável de admin/UI.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--file', required=True, help='Caminho do CSV com as inscrições antigas.')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Valida e reporta o que seria feito, sem gravar nada no banco nem enviar e-mails.',
        )

    def handle(self, *args, **options):
        try:
            with open(options['file'], newline='', encoding='utf-8') as arquivo:
                linhas = list(csv.DictReader(arquivo))
        except OSError as erro:
            raise CommandError(f"Não foi possível abrir '{options['file']}': {erro}")

        if not linhas:
            self.stdout.write(self.style.WARNING('Planilha vazia — nada para importar.'))
            return

        resultado = importar_linhas(linhas, dry_run=options['dry_run'])

        for numero, tipo, mensagem in resultado.mensagens:
            estilo = getattr(self.style, ESTILO_POR_TIPO[tipo])
            self.stdout.write(estilo(f'Linha {numero}: {mensagem}'))

        prefixo = '[dry-run] ' if options['dry_run'] else ''
        self.stdout.write(self.style.SUCCESS(
            f'{prefixo}{resultado.importadas} importada(s), {resultado.puladas} já existiam, '
            f'{resultado.com_erro} com erro.'
        ))
