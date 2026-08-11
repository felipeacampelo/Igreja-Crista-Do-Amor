import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api } from '../services/api'

type AuthContextValue = {
  token: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

const STORAGE_KEY = 'admin_token'

function aplicarToken(token: string | null) {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Token ${token}`
  } else {
    delete api.defaults.headers.common['Authorization']
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY))

  useEffect(() => {
    aplicarToken(token)
  }, [token])

  async function login(email: string, password: string) {
    const response = await api.post<{ token: string }>('/api/auth/login/', { email, password })
    localStorage.setItem(STORAGE_KEY, response.data.token)
    setToken(response.data.token)
  }

  function logout() {
    localStorage.removeItem(STORAGE_KEY)
    setToken(null)
  }

  return <AuthContext.Provider value={{ token, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth precisa estar dentro de um AuthProvider')
  return context
}
