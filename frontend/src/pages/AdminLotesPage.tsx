import { useEffect, useState, type FormEvent } from 'react'
import { AlertCircle, Check } from 'lucide-react'
import { AdminShell } from '../components/AdminShell'
import { adminApi, formatApiErrors } from '../services/api'
import type { LoteAdmin } from '../types'

export function AdminLotesPage() {
  const [lotes, setLotes] = useState<LoteAdmin[] | null>(null)
  const [semPermissao, setSemPermissao] = useState(false)
  const [erros, setErros] = useState<string[]>([])
  const [salvando, setSalvando] = useState(false)

  const [nome, setNome] = useState('')
  const [preco, setPreco] = useState('')
  const [limiteVagas, setLimiteVagas] = useState('')

  function carregarLotes() {
    adminApi
      .get<LoteAdmin[]>('/api/admin/lotes/')
      .then((response) => {
        setSemPermissao(false)
        setLotes(response.data)
      })
      .catch((error) => {
        if (error?.response?.status === 403 || error?.response?.status === 401) {
          setSemPermissao(true)
        }
      })
  }

  useEffect(() => {
    carregarLotes()
  }, [])

  async function criarLote(event: FormEvent) {
    event.preventDefault()
    setErros([])
    setSalvando(true)

    try {
      await adminApi.post('/api/admin/lotes/', {
        nome, preco, limite_vagas: limiteVagas, ativo: false,
      })
      setNome('')
      setPreco('')
      setLimiteVagas('')
      carregarLotes()
    } catch (error: unknown) {
      const data = (error as { response?: { data?: unknown } })?.response?.data
      setErros(formatApiErrors(data))
    } finally {
      setSalvando(false)
    }
  }

  async function ativarLote(id: number) {
    await adminApi.patch(`/api/admin/lotes/${id}/`, { ativo: true })
    carregarLotes()
  }

  if (semPermissao) {
    return (
      <AdminShell>
        <p className="text-gray-600">Você não tem permissão para gerenciar lotes.</p>
      </AdminShell>
    )
  }

  if (!lotes) {
    return (
      <AdminShell>
        <p className="text-gray-600">Carregando...</p>
      </AdminShell>
    )
  }

  return (
    <AdminShell>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Lotes</h1>
        <p className="mt-1 text-sm text-gray-600">
          Só um lote fica ativo por vez — ativar um desativa o anterior automaticamente.
        </p>
      </div>

      <div className="card mb-6">
        <h2 className="mb-3 text-lg font-bold text-gray-900">Novo lote</h2>
        <form onSubmit={criarLote} className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="field-label">Nome</label>
            <input className="field-input" value={nome} onChange={(e) => setNome(e.target.value)} required />
          </div>
          <div>
            <label className="field-label">Preço</label>
            <input
              className="field-input"
              value={preco}
              onChange={(e) => setPreco(e.target.value)}
              placeholder="150.00"
              required
            />
          </div>
          <div>
            <label className="field-label">Limite de vagas</label>
            <input
              className="field-input"
              value={limiteVagas}
              onChange={(e) => setLimiteVagas(e.target.value)}
              required
            />
          </div>
          <div className="sm:col-span-3">
            <button type="submit" disabled={salvando} className="btn-primary disabled:opacity-50">
              {salvando ? 'Criando...' : 'Criar lote'}
            </button>
          </div>
        </form>
        {erros.length > 0 && (
          <div className="mt-4 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
            <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
            <ul className="space-y-1 text-sm text-red-800">
              {erros.map((erro) => (
                <li key={erro}>{erro}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="space-y-3">
        {lotes.map((lote) => (
          <div key={lote.id} className="card flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-gray-900">{lote.nome}</h3>
                {lote.ativo && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">
                    <Check className="h-3 w-3" />
                    Ativo
                  </span>
                )}
                {lote.esgotado && (
                  <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
                    Esgotado
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-600">
                R$ {lote.preco} · {lote.vagas_ocupadas}/{lote.limite_vagas} vagas ocupadas
              </p>
            </div>
            {!lote.ativo && (
              <button type="button" onClick={() => ativarLote(lote.id)} className="btn-secondary">
                Ativar
              </button>
            )}
          </div>
        ))}
      </div>
    </AdminShell>
  )
}
