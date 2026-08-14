import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertCircle } from 'lucide-react'
import { PublicHeader } from '../components/PublicHeader'
import { api, formatApiErrors } from '../services/api'
import type { Lote } from '../types'

function calculaIdade(dataNascimento: string): number | null {
  if (!dataNascimento) return null
  const nascimento = new Date(dataNascimento)
  if (Number.isNaN(nascimento.getTime())) return null

  const hoje = new Date()
  let idade = hoje.getFullYear() - nascimento.getFullYear()
  const aindaNaoFezAniversario =
    hoje.getMonth() < nascimento.getMonth() ||
    (hoje.getMonth() === nascimento.getMonth() && hoje.getDate() < nascimento.getDate())
  if (aindaNaoFezAniversario) idade -= 1
  return idade
}

function formatCpf(valor: string): string {
  const digitos = valor.replace(/\D/g, '').slice(0, 11)
  if (digitos.length > 9) return digitos.replace(/(\d{3})(\d{3})(\d{3})(\d{1,2})/, '$1.$2.$3-$4')
  if (digitos.length > 6) return digitos.replace(/(\d{3})(\d{3})(\d{1,3})/, '$1.$2.$3')
  if (digitos.length > 3) return digitos.replace(/(\d{3})(\d{1,3})/, '$1.$2')
  return digitos
}

function formatCelular(valor: string): string {
  const digitos = valor.replace(/\D/g, '').slice(0, 11)
  if (digitos.length > 7) return digitos.replace(/(\d{2})(\d{5})(\d{1,4})/, '($1) $2-$3')
  if (digitos.length > 2) return digitos.replace(/(\d{2})(\d{1,5})/, '($1) $2')
  return digitos
}

function hojeISO(): string {
  return new Date().toISOString().slice(0, 10)
}

export function InscricaoForm() {
  const navigate = useNavigate()
  const [lote, setLote] = useState<Lote | null>(null)
  const [carregado, setCarregado] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)

  const [nomeCompleto, setNomeCompleto] = useState('')
  const [cpf, setCpf] = useState('')
  const [email, setEmail] = useState('')
  const [sexo, setSexo] = useState('F')
  const [dataNascimento, setDataNascimento] = useState('')
  const [celular, setCelular] = useState('')
  const [cupomCodigo, setCupomCodigo] = useState('')
  const [nomeResponsavel, setNomeResponsavel] = useState('')
  const [celularResponsavel, setCelularResponsavel] = useState('')

  const idade = calculaIdade(dataNascimento)
  const menorDeIdade = idade !== null && idade < 18

  useEffect(() => {
    api
      .get<Lote | null>('/api/lotes/')
      .then((response) => setLote(response.data))
      .finally(() => setCarregado(true))
  }, [])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!lote) return

    if (dataNascimento > hojeISO()) {
      setErrors(['Data de nascimento não pode ser uma data futura.'])
      return
    }

    setErrors([])
    setSubmitting(true)

    try {
      const response = await api.post('/api/inscricoes/', {
        nome_completo: nomeCompleto,
        cpf,
        email,
        sexo,
        data_nascimento: dataNascimento,
        celular,
        lote: lote.id,
        cupom_codigo: cupomCodigo,
        nome_responsavel: menorDeIdade ? nomeResponsavel : '',
        celular_responsavel: menorDeIdade ? celularResponsavel : '',
      })
      navigate(`/inscricao/${response.data.token}`)
    } catch (error: unknown) {
      const data = (error as { response?: { data?: unknown } })?.response?.data
      setErrors(formatApiErrors(data))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen">
      <PublicHeader />

      <main className="mx-auto max-w-3xl px-4 py-10">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-gray-900 sm:text-3xl">Inscreva-se na Fire Conference</h1>
          <p className="mt-2 text-sm text-gray-600">Preencha seus dados para garantir sua vaga.</p>
        </div>

        {carregado && !lote && (
          <div className="card mb-6 border-2 border-gray-200 text-center text-gray-600">
            As inscrições estão fechadas no momento. Volte em breve.
          </div>
        )}

        {lote && (
          <div className="mb-6 flex items-center justify-between rounded-lg border-2 border-flame bg-white px-5 py-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-flame">Lote vigente</p>
              <p className="text-lg font-bold text-gray-900">{lote.nome}</p>
            </div>
            <p className="text-2xl font-bold text-flame">R$ {lote.preco}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="card space-y-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className="field-label">Nome completo</label>
              <input
                className="field-input"
                value={nomeCompleto}
                onChange={(e) => setNomeCompleto(e.target.value)}
                required
              />
            </div>

            <div>
              <label className="field-label">CPF</label>
              <input
                className="field-input"
                value={cpf}
                onChange={(e) => setCpf(formatCpf(e.target.value))}
                inputMode="numeric"
                placeholder="000.000.000-00"
                maxLength={14}
                required
              />
            </div>

            <div>
              <label className="field-label">E-mail</label>
              <input
                type="email"
                className="field-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div>
              <label className="field-label">Sexo</label>
              <select className="field-input" value={sexo} onChange={(e) => setSexo(e.target.value)}>
                <option value="F">Feminino</option>
                <option value="M">Masculino</option>
              </select>
            </div>

            <div>
              <label className="field-label">Data de nascimento</label>
              <input
                type="date"
                className="field-input"
                value={dataNascimento}
                onChange={(e) => setDataNascimento(e.target.value)}
                max={hojeISO()}
                required
              />
            </div>

            <div>
              <label className="field-label">Celular</label>
              <input
                className="field-input"
                value={celular}
                onChange={(e) => setCelular(formatCelular(e.target.value))}
                inputMode="numeric"
                placeholder="(12) 93456-7890"
                maxLength={15}
                required
              />
            </div>

            <div className="sm:col-span-2">
              <label className="field-label">Cupom (opcional)</label>
              <input
                className="field-input"
                value={cupomCodigo}
                onChange={(e) => setCupomCodigo(e.target.value)}
              />
            </div>
          </div>

          {menorDeIdade && (
            <div className="rounded-lg border border-ember-dark/30 bg-ember/10 p-4">
              <p className="mb-4 text-sm font-medium text-gray-800">
                Inscrito menor de idade: informe os dados do responsável.
              </p>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="field-label">Nome do responsável</label>
                  <input
                    className="field-input"
                    value={nomeResponsavel}
                    onChange={(e) => setNomeResponsavel(e.target.value)}
                    required
                  />
                </div>
                <div>
                  <label className="field-label">Celular do responsável</label>
                  <input
                    className="field-input"
                    value={celularResponsavel}
                    onChange={(e) => setCelularResponsavel(formatCelular(e.target.value))}
                    inputMode="numeric"
                    placeholder="(12) 93456-7890"
                    maxLength={15}
                    required
                  />
                </div>
              </div>
            </div>
          )}

          {errors.length > 0 && (
            <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
              <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
              <ul className="space-y-1 text-sm text-red-800">
                {errors.map((error) => (
                  <li key={error}>{error}</li>
                ))}
              </ul>
            </div>
          )}

          <button
            type="submit"
            disabled={submitting || !lote}
            className="btn-primary w-full disabled:opacity-50"
          >
            {submitting ? 'Enviando...' : 'Inscrever-se'}
          </button>
        </form>
      </main>
    </div>
  )
}
