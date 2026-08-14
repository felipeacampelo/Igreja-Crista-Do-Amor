import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, Flame, Lock, Mail } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { formatApiErrors } from '../services/api'

export function AdminLoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [erro, setErro] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setErro('')
    setEnviando(true)

    try {
      await login(email, password)
      navigate('/admin')
    } catch (error: unknown) {
      const response = (error as { response?: { data?: unknown; status?: number } })?.response
      if (response) {
        setErro(formatApiErrors(response.data).join(' ') || 'Email ou senha inválidos.')
      } else {
        // Sem response: erro de rede, CORS, ou resposta em formato inesperado
        // (ex: URL da API mal configurada) — não é "senha errada".
        setErro('Não foi possível conectar ao servidor. Tente novamente em instantes.')
      }
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-black to-gray-900 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <Flame className="mx-auto mb-3 h-10 w-10 text-flame" />
          <h1 className="mb-1 text-2xl font-bold text-ember">Administrativo</h1>
          <p className="text-sm text-gray-300">Fire Conference</p>
        </div>

        <div className="card">
          {erro && (
            <div className="mb-6 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
              <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
              <p className="text-sm text-red-800">{erro}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="field-label">
                <Mail className="mr-1.5 inline h-4 w-4" />
                Email
              </label>
              <input
                type="email"
                className="field-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div>
              <label className="field-label">
                <Lock className="mr-1.5 inline h-4 w-4" />
                Senha
              </label>
              <input
                type="password"
                className="field-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <button type="submit" disabled={enviando} className="btn-primary w-full disabled:opacity-50">
              {enviando ? 'Entrando...' : 'Entrar'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
