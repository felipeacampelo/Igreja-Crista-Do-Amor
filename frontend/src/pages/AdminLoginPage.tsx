import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

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
      navigate('/admin/fila-aprovacao')
    } catch {
      setErro('Email ou senha inválidos.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <>
      <h1>Admin — Fire Conference</h1>
      <form onSubmit={handleSubmit}>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Senha
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {erro && <p>{erro}</p>}
        <button type="submit" disabled={enviando}>
          {enviando ? 'Entrando...' : 'Entrar'}
        </button>
      </form>
    </>
  )
}
