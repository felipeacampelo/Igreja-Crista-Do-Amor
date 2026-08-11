import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { PrivateAdminRoute } from './components/PrivateAdminRoute'
import { AuthProvider } from './contexts/AuthContext'
import { AdminFilaAprovacaoPage } from './pages/AdminFilaAprovacaoPage'
import { AdminLoginPage } from './pages/AdminLoginPage'
import { InscricaoForm } from './pages/InscricaoForm'
import { InscricaoStatusPage } from './pages/InscricaoStatusPage'
import './App.css'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<InscricaoForm />} />
          <Route path="/inscricao/:token" element={<InscricaoStatusPage />} />
          <Route path="/admin/login" element={<AdminLoginPage />} />
          <Route
            path="/admin/fila-aprovacao"
            element={
              <PrivateAdminRoute>
                <AdminFilaAprovacaoPage />
              </PrivateAdminRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
