import { useEffect, useState } from 'react'
import { AlertCircle, Check, FileText, X } from 'lucide-react'
import { AdminShell } from '../components/AdminShell'
import { adminApi, formatApiErrors } from '../services/api'
import type { InscricaoFilaAprovacao } from '../types'

const SEXO_LABEL: Record<InscricaoFilaAprovacao['sexo'], string> = {
  F: 'Feminino',
  M: 'Masculino',
}

export function AdminFilaAprovacaoPage() {
  const [fila, setFila] = useState<InscricaoFilaAprovacao[] | null>(null)
  const [semPermissao, setSemPermissao] = useState(false)
  const [erros, setErros] = useState<Record<number, string[]>>({})
  const [rejeitando, setRejeitando] = useState<Record<number, boolean>>({})
  const [motivos, setMotivos] = useState<Record<number, string>>({})

  function carregarFila() {
    adminApi
      .get<InscricaoFilaAprovacao[]>('/api/admin/inscricoes/fila-aprovacao/')
      .then((response) => {
        setSemPermissao(false)
        setFila(response.data)
      })
      .catch((error) => {
        if (error?.response?.status === 403 || error?.response?.status === 401) {
          setSemPermissao(true)
        }
      })
  }

  useEffect(() => {
    carregarFila()
  }, [])

  async function aprovar(id: number) {
    setErros((prev) => ({ ...prev, [id]: [] }))
    try {
      await adminApi.post(`/api/admin/inscricoes/${id}/aprovar/`)
      carregarFila()
    } catch (error: unknown) {
      const data = (error as { response?: { data?: unknown } })?.response?.data
      setErros((prev) => ({ ...prev, [id]: formatApiErrors(data) }))
    }
  }

  async function confirmarRejeicao(id: number) {
    const motivo = (motivos[id] ?? '').trim()
    if (!motivo) {
      setErros((prev) => ({ ...prev, [id]: ['Informe o motivo da rejeição.'] }))
      return
    }

    setErros((prev) => ({ ...prev, [id]: [] }))
    try {
      await adminApi.post(`/api/admin/inscricoes/${id}/rejeitar/`, { motivo })
      carregarFila()
    } catch (error: unknown) {
      const data = (error as { response?: { data?: unknown } })?.response?.data
      setErros((prev) => ({ ...prev, [id]: formatApiErrors(data) }))
    }
  }

  if (semPermissao) {
    return (
      <AdminShell>
        <p className="text-gray-600">Você não tem permissão para acessar a fila de aprovação.</p>
      </AdminShell>
    )
  }

  if (!fila) {
    return (
      <AdminShell>
        <p className="text-gray-600">Carregando...</p>
      </AdminShell>
    )
  }

  return (
    <AdminShell>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Fila de aprovação</h1>
        <p className="mt-1 text-sm text-gray-600">
          {fila.length} inscrição(ões) aguardando revisão.
        </p>
      </div>

      {fila.length === 0 && (
        <div className="card text-center text-gray-600">Nenhuma inscrição aguardando revisão.</div>
      )}

      <div className="space-y-4">
        {fila.map((inscricao) => (
          <div key={inscricao.id} className="card">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-gray-900">{inscricao.nome_completo}</h2>
                <p className="text-sm text-gray-600">
                  {inscricao.lote}
                  {inscricao.cupom && ` · Cupom: ${inscricao.cupom}`}
                </p>
              </div>
              <p className="text-xl font-bold text-gray-900">R$ {inscricao.preco_final}</p>
            </div>

            <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-gray-500">CPF</dt>
                <dd className="text-gray-900">{inscricao.cpf}</dd>
              </div>
              <div>
                <dt className="text-gray-500">E-mail</dt>
                <dd className="text-gray-900">{inscricao.email}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Celular</dt>
                <dd className="text-gray-900">{inscricao.celular}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Sexo</dt>
                <dd className="text-gray-900">{SEXO_LABEL[inscricao.sexo]}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Data de nascimento</dt>
                <dd className="text-gray-900">{inscricao.data_nascimento}</dd>
              </div>
            </dl>

            <div className="mt-4">
              {inscricao.comprovante_url ? (
                <a
                  href={inscricao.comprovante_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-flame hover:text-flame-dark"
                >
                  <FileText className="h-4 w-4" />
                  Ver comprovante
                </a>
              ) : (
                <p className="text-sm text-gray-500">Comprovante indisponível no momento.</p>
              )}
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => aprovar(inscricao.id)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-green-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-green-700"
              >
                <Check className="h-4 w-4" />
                Aprovar
              </button>
              <button
                type="button"
                onClick={() => setRejeitando((prev) => ({ ...prev, [inscricao.id]: true }))}
                className="inline-flex items-center gap-1.5 rounded-lg border border-red-300 px-4 py-2 text-sm font-semibold text-red-700 transition-colors hover:bg-red-50"
              >
                <X className="h-4 w-4" />
                Rejeitar
              </button>
            </div>

            {rejeitando[inscricao.id] && (
              <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
                <label className="field-label">Motivo da rejeição</label>
                <input
                  className="field-input"
                  value={motivos[inscricao.id] ?? ''}
                  onChange={(e) => setMotivos((prev) => ({ ...prev, [inscricao.id]: e.target.value }))}
                />
                <button
                  type="button"
                  onClick={() => confirmarRejeicao(inscricao.id)}
                  className="btn-secondary mt-3"
                >
                  Confirmar rejeição
                </button>
              </div>
            )}

            {erros[inscricao.id]?.length > 0 && (
              <div className="mt-4 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
                <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
                <ul className="space-y-1 text-sm text-red-800">
                  {erros[inscricao.id].map((erro) => (
                    <li key={erro}>{erro}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </AdminShell>
  )
}
