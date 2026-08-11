import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { InscricaoForm } from './pages/InscricaoForm'
import { InscricaoStatusPage } from './pages/InscricaoStatusPage'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<InscricaoForm />} />
        <Route path="/inscricao/:token" element={<InscricaoStatusPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
