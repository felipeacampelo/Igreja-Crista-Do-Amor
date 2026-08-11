import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
})

export function formatApiErrors(data: unknown): string[] {
  if (!data || typeof data !== 'object') return ['Erro inesperado. Tente novamente.']

  return Object.values(data as Record<string, unknown>).flatMap((value) =>
    (Array.isArray(value) ? value : [value]).map(String),
  )
}
