import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { PrivateAdminRoute } from './components/PrivateAdminRoute'
import { AuthProvider } from './contexts/AuthContext'
import { AdminCheckinPage } from './pages/AdminCheckinPage'
import { AdminCuponsPage } from './pages/AdminCuponsPage'
import { AdminDashboardPage } from './pages/AdminDashboardPage'
import { AdminFilaAprovacaoPage } from './pages/AdminFilaAprovacaoPage'
import { AdminLoginPage } from './pages/AdminLoginPage'
import { AdminLotesPage } from './pages/AdminLotesPage'
import { Home } from './pages/Home'
import { InscricaoForm } from './pages/InscricaoForm'
import { InscricaoStatusPage } from './pages/InscricaoStatusPage'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/inscricao" element={<InscricaoForm />} />
          <Route path="/inscricao/:token" element={<InscricaoStatusPage />} />
          <Route path="/admin/login" element={<AdminLoginPage />} />
          <Route
            path="/admin"
            element={
              <PrivateAdminRoute>
                <AdminDashboardPage />
              </PrivateAdminRoute>
            }
          />
          <Route
            path="/admin/fila-aprovacao"
            element={
              <PrivateAdminRoute>
                <AdminFilaAprovacaoPage />
              </PrivateAdminRoute>
            }
          />
          <Route
            path="/admin/checkin"
            element={
              <PrivateAdminRoute>
                <AdminCheckinPage />
              </PrivateAdminRoute>
            }
          />
          <Route
            path="/admin/lotes"
            element={
              <PrivateAdminRoute>
                <AdminLotesPage />
              </PrivateAdminRoute>
            }
          />
          <Route
            path="/admin/cupons"
            element={
              <PrivateAdminRoute>
                <AdminCuponsPage />
              </PrivateAdminRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
