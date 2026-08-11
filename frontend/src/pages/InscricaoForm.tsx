import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
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

export function InscricaoForm() {
  const navigate = useNavigate()
  const [lotes, setLotes] = useState<Lote[]>([])
  const [errors, setErrors] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)

  const [nomeCompleto, setNomeCompleto] = useState('')
  const [cpf, setCpf] = useState('')
  const [email, setEmail] = useState('')
  const [sexo, setSexo] = useState('F')
  const [dataNascimento, setDataNascimento] = useState('')
  const [celular, setCelular] = useState('')
  const [loteId, setLoteId] = useState('')
  const [cupomCodigo, setCupomCodigo] = useState('')
  const [nomeResponsavel, setNomeResponsavel] = useState('')
  const [celularResponsavel, setCelularResponsavel] = useState('')

  const idade = calculaIdade(dataNascimento)
  const menorDeIdade = idade !== null && idade < 18

  useEffect(() => {
    api.get<Lote[]>('/api/lotes/').then((response) => setLotes(response.data))
  }, [])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
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
        lote: loteId,
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
    <>
      <h1>Fire Conference</h1>
      <form onSubmit={handleSubmit}>
        <label>
          Nome completo
          <input value={nomeCompleto} onChange={(e) => setNomeCompleto(e.target.value)} required />
        </label>

        <label>
          CPF
          <input value={cpf} onChange={(e) => setCpf(e.target.value)} required />
        </label>

        <label>
          E-mail
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>

        <label>
          Sexo
          <select value={sexo} onChange={(e) => setSexo(e.target.value)}>
            <option value="F">Feminino</option>
            <option value="M">Masculino</option>
          </select>
        </label>

        <label>
          Data de nascimento
          <input
            type="date"
            value={dataNascimento}
            onChange={(e) => setDataNascimento(e.target.value)}
            required
          />
        </label>

        <label>
          Celular
          <input value={celular} onChange={(e) => setCelular(e.target.value)} required />
        </label>

        <label>
          Lote
          <select value={loteId} onChange={(e) => setLoteId(e.target.value)} required>
            <option value="" disabled>
              Selecione um lote
            </option>
            {lotes.map((lote) => (
              <option key={lote.id} value={lote.id}>
                {lote.nome} — R$ {lote.preco} ({lote.vagas_restantes} vagas)
              </option>
            ))}
          </select>
        </label>

        <label>
          Cupom (opcional)
          <input value={cupomCodigo} onChange={(e) => setCupomCodigo(e.target.value)} />
        </label>

        {menorDeIdade && (
          <>
            <p>Inscrito menor de idade: informe os dados do responsável.</p>
            <label>
              Nome do responsável
              <input value={nomeResponsavel} onChange={(e) => setNomeResponsavel(e.target.value)} required />
            </label>
            <label>
              Celular do responsável
              <input
                value={celularResponsavel}
                onChange={(e) => setCelularResponsavel(e.target.value)}
                required
              />
            </label>
          </>
        )}

        {errors.length > 0 && (
          <ul>
            {errors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        )}

        <button type="submit" disabled={submitting}>
          {submitting ? 'Enviando...' : 'Inscrever-se'}
        </button>
      </form>
    </>
  )
}
