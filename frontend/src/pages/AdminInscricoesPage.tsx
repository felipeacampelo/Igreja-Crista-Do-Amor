import { useCallback, useEffect, useState } from 'react'
import { AlertCircle, FileText, Search } from 'lucide-react'
import { AdminShell } from '../components/AdminShell'
import { adminApi, formatApiErrors } from '../services/api'
import type { InscricaoAdmin, InscricaoSituacao } from '../types'

const STATUS_LABEL: Record<InscricaoSituacao, string> = {
  pendente: 'Falta comprovante',
  comprovante_enviado: 'Aguardando aprovação',
  confirmada: 'Aprovada',
  rejeitada: 'Rejeitada',
}

const STATUS_BADGE: Record<InscricaoSituacao, string> = {
  pendente: 'bg-ember/15 text-ember-dark',
  comprovante_enviado: 'bg-blue-100 text-blue-700',
  confirmada: 'bg-green-100 text-green-700',
  rejeitada: 'bg-red-100 text-red-700',
}

const SITUACOES: InscricaoSituacao[] = ['pendente', 'comprovante_enviado', 'confirmada', 'rejeitada']

const ORDENACOES = [
  { valor: '-criado_em', label: 'Mais recentes' },
  { valor: 'criado_em', label: 'Mais antigas' },
  { valor: 'nome_completo', label: 'Nome (A–Z)' },
  { valor: '-nome_completo', label: 'Nome (Z–A)' },
  { valor: 'status', label: 'Situação' },
  { valor: '-preco_final', label: 'Maior valor' },
  { valor: 'preco_final', label: 'Menor valor' },
]

function formatData(iso: string) {
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export function AdminInscricoesPage() {
  const [inscricoes, setInscricoes] = useState<InscricaoAdmin[] | null>(null)
  const [semPermissao, setSemPermissao] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  const [busca, setBusca] = useState('')
  const [buscaAplicada, setBuscaAplicada] = useState('')
  const [situacao, setSituacao] = useState<InscricaoSituacao | ''>('')
  const [ordenacao, setOrdenacao] = useState('-criado_em')

  // Linha em edição de veredito e o status escolhido nela.
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [novoStatus, setNovoStatus] = useState<InscricaoSituacao>('confirmada')
  const [motivo, setMotivo] = useState('')
  const [salvandoId, setSalvandoId] = useState<number | null>(null)

  const carregar = useCallback(() => {
    const params = new URLSearchParams({ ordering: ordenacao })
    if (buscaAplicada) params.set('q', buscaAplicada)
    if (situacao) params.set('status', situacao)

    adminApi
      .get<InscricaoAdmin[]>(`/api/admin/inscricoes/?${params}`)
      .then((response) => {
        setSemPermissao(false)
        setInscricoes(response.data)
      })
      .catch((error) => {
        if (error?.response?.status === 403 || error?.response?.status === 401) {
          setSemPermissao(true)
        } else {
          setErro('Não foi possível carregar as inscrições.')
        }
      })
  }, [buscaAplicada, situacao, ordenacao])

  useEffect(() => {
    carregar()
  }, [carregar])

  // A busca só vai ao servidor depois de uma pausa na digitação — sem isso é uma
  // requisição por tecla.
  useEffect(() => {
    const timer = setTimeout(() => setBuscaAplicada(busca.trim()), 400)
    return () => clearTimeout(timer)
  }, [busca])

  function abrirEdicao(inscricao: InscricaoAdmin) {
    setEditandoId(inscricao.id)
    setNovoStatus(inscricao.status === 'confirmada' ? 'rejeitada' : 'confirmada')
    setMotivo('')
    setErro(null)
  }

  async function salvarStatus(id: number) {
    setErro(null)
    setSalvandoId(id)

    try {
      await adminApi.post(`/api/admin/inscricoes/${id}/status/`, {
        status: novoStatus,
        motivo: novoStatus === 'rejeitada' ? motivo : '',
      })
      setEditandoId(null)
      carregar()
    } catch (error: unknown) {
      const data = (error as { response?: { data?: unknown } })?.response?.data
      setErro(formatApiErrors(data)[0] ?? 'Não foi possível alterar a situação.')
    } finally {
      setSalvandoId(null)
    }
  }

  async function verComprovante(id: number) {
    setErro(null)
    try {
      const response = await adminApi.get<{ url: string }>(`/api/admin/inscricoes/${id}/comprovante-url/`)
      window.open(response.data.url, '_blank', 'noopener,noreferrer')
    } catch (error: unknown) {
      const data = (error as { response?: { data?: unknown } })?.response?.data
      setErro(formatApiErrors(data)[0] ?? 'Não foi possível abrir o comprovante.')
    }
  }

  if (semPermissao) {
    return (
      <AdminShell>
        <p className="text-gray-600">Você não tem permissão para ver as inscrições.</p>
      </AdminShell>
    )
  }

  return (
    <AdminShell>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Inscrições</h1>
        <p className="mt-1 text-sm text-gray-600">
          Lista completa — busque, filtre por situação e corrija um veredito quando necessário.
        </p>
      </div>

      <div className="card mb-6 grid gap-4 sm:grid-cols-3">
        <div className="sm:col-span-3 lg:col-span-1">
          <label className="field-label">Buscar</label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              className="field-input pl-9"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Nome, CPF, e-mail ou código"
            />
          </div>
        </div>

        <div>
          <label className="field-label">Situação</label>
          <select
            className="field-input"
            value={situacao}
            onChange={(e) => setSituacao(e.target.value as InscricaoSituacao | '')}
          >
            <option value="">Todas</option>
            {SITUACOES.map((valor) => (
              <option key={valor} value={valor}>
                {STATUS_LABEL[valor]}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="field-label">Ordenar por</label>
          <select className="field-input" value={ordenacao} onChange={(e) => setOrdenacao(e.target.value)}>
            {ORDENACOES.map(({ valor, label }) => (
              <option key={valor} value={valor}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {erro && (
        <div className="mb-4 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
          <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
          <p className="text-sm text-red-800">{erro}</p>
        </div>
      )}

      {!inscricoes ? (
        <p className="text-gray-600">Carregando...</p>
      ) : inscricoes.length === 0 ? (
        <div className="card text-center text-gray-600">Nenhuma inscrição encontrada.</div>
      ) : (
        <>
          <p className="mb-3 text-sm text-gray-600">{inscricoes.length} inscrição(ões)</p>

          <div className="space-y-3">
            {inscricoes.map((inscricao) => (
              <div key={inscricao.id} className="card">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-bold text-gray-900">{inscricao.nome_completo}</h3>
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_BADGE[inscricao.status]}`}
                      >
                        {STATUS_LABEL[inscricao.status]}
                      </span>
                      {inscricao.checkin_em && (
                        <span className="rounded-full bg-gray-200 px-2 py-0.5 text-xs font-semibold text-gray-700">
                          Check-in feito
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-sm text-gray-600">
                      {inscricao.cpf} · {inscricao.email} · {inscricao.celular}
                    </p>
                    <p className="mt-1 text-sm text-gray-600">
                      {inscricao.lote} · R$ {inscricao.preco_final}
                      {inscricao.cupom && ` · Cupom: ${inscricao.cupom}`} · Código:{' '}
                      <span className="font-mono">{inscricao.codigo_checkin}</span> ·{' '}
                      {formatData(inscricao.criado_em)}
                    </p>
                    {inscricao.status === 'rejeitada' && inscricao.motivo_rejeicao && (
                      <p className="mt-2 text-sm text-red-700">Motivo: {inscricao.motivo_rejeicao}</p>
                    )}
                  </div>

                  <div className="flex flex-shrink-0 items-center gap-2">
                    {inscricao.tem_comprovante && (
                      <button
                        type="button"
                        onClick={() => verComprovante(inscricao.id)}
                        className="btn-secondary inline-flex items-center gap-1.5"
                      >
                        <FileText className="h-4 w-4" />
                        Comprovante
                      </button>
                    )}
                    {editandoId !== inscricao.id && !inscricao.checkin_em && (
                      <button type="button" onClick={() => abrirEdicao(inscricao)} className="btn-secondary">
                        Alterar situação
                      </button>
                    )}
                  </div>
                </div>

                {editandoId === inscricao.id && (
                  <div className="mt-4 space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div>
                        <label className="field-label">Nova situação</label>
                        <select
                          className="field-input"
                          value={novoStatus}
                          onChange={(e) => setNovoStatus(e.target.value as InscricaoSituacao)}
                        >
                          {SITUACOES.filter((valor) => valor !== inscricao.status).map((valor) => (
                            <option key={valor} value={valor}>
                              {STATUS_LABEL[valor]}
                            </option>
                          ))}
                        </select>
                      </div>
                      {novoStatus === 'rejeitada' && (
                        <div>
                          <label className="field-label">Motivo da rejeição</label>
                          <input
                            className="field-input"
                            value={motivo}
                            onChange={(e) => setMotivo(e.target.value)}
                            placeholder="Ex: pagamento não localizado"
                          />
                        </div>
                      )}
                    </div>

                    <p className="text-xs text-gray-600">
                      {novoStatus === 'confirmada'
                        ? 'Ao aprovar, o ingresso com QR code é enviado por e-mail para o inscrito.'
                        : 'O inscrito vê essa mudança na página de status da inscrição dele.'}
                    </p>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => salvarStatus(inscricao.id)}
                        disabled={salvandoId === inscricao.id}
                        className="btn-primary disabled:opacity-50"
                      >
                        {salvandoId === inscricao.id ? 'Salvando...' : 'Salvar'}
                      </button>
                      <button type="button" onClick={() => setEditandoId(null)} className="btn-secondary">
                        Cancelar
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </AdminShell>
  )
}
