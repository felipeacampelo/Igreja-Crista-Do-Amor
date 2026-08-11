import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
})

// Instância separada para chamadas autenticadas do admin — o token nunca
// deve viajar em requisições públicas (ex: a página de status). Um token
// inválido/expirado faria o DRF rejeitar a requisição com 401 mesmo em
// endpoints públicos (AllowAny), já que a autenticação é checada antes da
// permissão.
export const adminApi = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
})

export function formatApiErrors(data: unknown): string[] {
  if (!data || typeof data !== 'object') return ['Erro inesperado. Tente novamente.']

  return Object.values(data as Record<string, unknown>).flatMap((value) =>
    (Array.isArray(value) ? value : [value]).map(String),
  )
}
