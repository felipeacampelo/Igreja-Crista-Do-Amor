import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export function PrivateAdminRoute({ children }: { children: ReactNode }) {
  const { token } = useAuth()

  if (!token) {
    return <Navigate to="/admin/login" replace />
  }

  return <>{children}</>
}
