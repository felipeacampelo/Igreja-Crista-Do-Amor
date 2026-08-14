import { useEffect, useState, type FormEvent } from 'react'
import { AlertCircle, Trash2 } from 'lucide-react'
import { AdminShell } from '../components/AdminShell'
import { adminApi, formatApiErrors } from '../services/api'
import type { CupomAdmin } from '../types'

export function AdminCuponsPage() {
  const [cupons, setCupons] = useState<CupomAdmin[] | null>(null)
  const [semPermissao, setSemPermissao] = useState(false)
  const [erros, setErros] = useState<string[]>([])
  const [salvando, setSalvando] = useState(false)
  const [erroExclusao, setErroExclusao] = useState<string | null>(null)
  const [excluindoId, setExcluindoId] = useState<number | null>(null)

  const [codigo, setCodigo] = useState('')
  const [valorDesconto, setValorDesconto] = useState('')
  const [limiteUsos, setLimiteUsos] = useState('')

  function carregarCupons() {
    adminApi
      .get<CupomAdmin[]>('/api/admin/cupons/')
      .then((response) => {
        setSemPermissao(false)
        setCupons(response.data)
      })
      .catch((error) => {
        if (error?.response?.status === 403 || error?.response?.status === 401) {
          setSemPermissao(true)
        }
      })
  }

  useEffect(() => {
    carregarCupons()
  }, [])

  async function criarCupom(event: FormEvent) {
    event.preventDefault()
    setErros([])
    setSalvando(true)

    try {
      await adminApi.post('/api/admin/cupons/', {
        codigo, valor_desconto: valorDesconto, limite_usos: limiteUsos,
      })
      setCodigo('')
      setValorDesconto('')
      setLimiteUsos('')
      carregarCupons()
    } catch (error: unknown) {
      const data = (error as { response?: { data?: unknown } })?.response?.data
      setErros(formatApiErrors(data))
    } finally {
      setSalvando(false)
    }
  }

  async function excluirCupom(id: number, codigo: string) {
    if (!window.confirm(`Excluir o cupom "${codigo}"? Essa ação não pode ser desfeita.`)) return

    setErroExclusao(null)
    setExcluindoId(id)

    try {
      await adminApi.delete(`/api/admin/cupons/${id}/`)
      carregarCupons()
    } catch (error: unknown) {
      const data = (error as { response?: { data?: unknown } })?.response?.data
      setErroExclusao(formatApiErrors(data)[0] ?? 'Não foi possível excluir o cupom.')
    } finally {
      setExcluindoId(null)
    }
  }

  if (semPermissao) {
    return (
      <AdminShell>
        <p className="text-gray-600">Você não tem permissão para gerenciar cupons.</p>
      </AdminShell>
    )
  }

  if (!cupons) {
    return (
      <AdminShell>
        <p className="text-gray-600">Carregando...</p>
      </AdminShell>
    )
  }

  return (
    <AdminShell>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Cupons</h1>
        <p className="mt-1 text-sm text-gray-600">Cupons de desconto disponíveis na inscrição.</p>
      </div>

      <div className="card mb-6">
        <h2 className="mb-3 text-lg font-bold text-gray-900">Novo cupom</h2>
        <form onSubmit={criarCupom} className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="field-label">Código</label>
            <input className="field-input" value={codigo} onChange={(e) => setCodigo(e.target.value)} required />
          </div>
          <div>
            <label className="field-label">Valor de desconto</label>
            <input
              className="field-input"
              value={valorDesconto}
              onChange={(e) => setValorDesconto(e.target.value)}
              placeholder="20.00"
              required
            />
          </div>
          <div>
            <label className="field-label">Limite de usos</label>
            <input
              className="field-input"
              value={limiteUsos}
              onChange={(e) => setLimiteUsos(e.target.value)}
              required
            />
          </div>
          <div className="sm:col-span-3">
            <button type="submit" disabled={salvando} className="btn-primary disabled:opacity-50">
              {salvando ? 'Criando...' : 'Criar cupom'}
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

      {erroExclusao && (
        <div className="mb-4 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
          <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
          <p className="text-sm text-red-800">{erroExclusao}</p>
        </div>
      )}

      <div className="space-y-3">
        {cupons.length === 0 && <div className="card text-center text-gray-600">Nenhum cupom cadastrado.</div>}
        {cupons.map((cupom) => (
          <div key={cupom.id} className="card flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-mono font-bold text-gray-900">{cupom.codigo}</h3>
                {cupom.esgotado && (
                  <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
                    Esgotado
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-600">
                Desconto de R$ {cupom.valor_desconto} · {cupom.usos_count}/{cupom.limite_usos} usos
              </p>
            </div>
            <button
              type="button"
              onClick={() => excluirCupom(cupom.id, cupom.codigo)}
              disabled={excluindoId === cupom.id}
              title="Excluir cupom"
              className="inline-flex items-center gap-1 rounded-lg border border-red-200 px-3 py-2 text-sm font-semibold text-red-600 transition-colors hover:bg-red-50 disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" />
              {excluindoId === cupom.id ? 'Excluindo...' : 'Excluir'}
            </button>
          </div>
        ))}
      </div>
    </AdminShell>
  )
}
