"""
Importação da planilha antiga (issue #11) — lógica por trás do management
command `importar_planilha`, script pontual (não é feature reaproveitável de
admin/UI, ver Out of Scope da issue #1).

Reaproveita InscricaoCreateSerializer para manter a mesma validação e cálculo
de preço do formulário público (idade/responsável, cupom, esgotamento de
lote) — só sobrescreve status e origem depois de criar a inscrição.

Idempotente por CPF: uma linha cujo CPF já existe em alguma Inscricao é
pulada (não é erro) — rodar o comando de novo não duplica inscrições.

Só lê CSV, não XLSX: a issue #1 deixou o formato em aberto ("a confirmar no
momento da execução") e nenhum dos dois projetos de referência (AreaMais,
Mio-Festa-2026) usa biblioteca de XLSX — exportar a planilha pra CSV antes
de rodar é mais simples do que adicionar uma dependência nova pra um script
que roda uma única vez.

Formato esperado de cada linha (dict — ver csv.DictReader no comando):
    nome_completo, cpf, email, sexo (M/F), data_nascimento (AAAA-MM-DD),
    celular, nome_responsavel (obrigatório se menor), celular_responsavel
    (obrigatório se menor), lote (nome do Lote já cadastrado), cupom_codigo
    (opcional).
"""
from collections import defaultdict
from dataclasses import dataclass, field

from django.db import transaction

from apps.lotes.models import Lote

from .models import Inscricao
from .notificacoes import enviar_ingresso_email_seguro
from .serializers import InscricaoCreateSerializer

CAMPOS_TEXTO = (
    'nome_completo', 'cpf', 'email', 'sexo', 'data_nascimento', 'celular',
    'nome_responsavel', 'celular_responsavel', 'cupom_codigo',
)


@dataclass
class ResultadoImportacao:
    importadas: int = 0
    puladas: int = 0
    com_erro: int = 0
    mensagens: list = field(default_factory=list)  # (numero_da_linha, 'ok'|'pulada'|'erro', texto)


def importar_linhas(linhas, dry_run=False):
    resultado = ResultadoImportacao()
    # Só usado em dry_run: nada é gravado, então lote.esgotado/cupom.esgotado
    # (calculados a partir do banco) não veem as linhas já "aceitas" nesta
    # mesma simulação — sem isso, um dry-run reportaria como válidas mais
    # linhas do que uma rodada real de fato conseguiria importar.
    reservas_lote = defaultdict(int)
    reservas_cupom = defaultdict(int)

    for numero, linha in enumerate(linhas, start=2):  # linha 1 é o cabeçalho
        dados = {campo: (linha.get(campo) or '').strip() for campo in CAMPOS_TEXTO}
        dados['sexo'] = dados['sexo'].upper()

        if not dados['cpf']:
            resultado.com_erro += 1
            resultado.mensagens.append((numero, 'erro', 'CPF em branco.'))
            continue

        if Inscricao.objects.filter(cpf=dados['cpf']).exists():
            resultado.puladas += 1
            resultado.mensagens.append((numero, 'pulada', f"CPF {dados['cpf']} já importado."))
            continue

        nome_lote = (linha.get('lote') or '').strip()
        lote = Lote.objects.filter(nome__iexact=nome_lote).first()
        if lote is None:
            resultado.com_erro += 1
            resultado.mensagens.append((numero, 'erro', f"Lote '{nome_lote}' não encontrado."))
            continue

        if dry_run and lote.vagas_ocupadas + reservas_lote[lote.id] >= lote.limite_vagas:
            resultado.com_erro += 1
            resultado.mensagens.append(
                (numero, 'erro', f"Lote '{lote.nome}' esgotado (considerando linhas anteriores desta simulação)."),
            )
            continue
        dados['lote'] = lote.id

        serializer = InscricaoCreateSerializer(data=dados)
        if not serializer.is_valid():
            resultado.com_erro += 1
            resultado.mensagens.append((numero, 'erro', str(serializer.errors)))
            continue

        if dry_run:
            cupom = serializer.validated_data.get('cupom')
            if cupom and cupom.usos_count + reservas_cupom[cupom.id] >= cupom.limite_usos:
                resultado.com_erro += 1
                resultado.mensagens.append((
                    numero, 'erro',
                    f"Cupom '{cupom.codigo}' esgotado (considerando linhas anteriores desta simulação).",
                ))
                continue

            reservas_lote[lote.id] += 1
            if cupom:
                reservas_cupom[cupom.id] += 1
            resultado.importadas += 1
            resultado.mensagens.append((numero, 'ok', f"{dados['nome_completo']} (simulado, nada foi gravado)."))
            continue

        with transaction.atomic():
            inscricao = serializer.save(origem=Inscricao.Origem.IMPORTACAO)
            inscricao.status = Inscricao.Status.CONFIRMADA
            inscricao.save(update_fields=['status', 'atualizado_em'])

        enviar_ingresso_email_seguro(inscricao)
        resultado.importadas += 1
        resultado.mensagens.append((numero, 'ok', f"{dados['nome_completo']} importada."))

    return resultado
