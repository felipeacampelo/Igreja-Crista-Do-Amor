import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Calendar, QrCode, Ticket, Wallet } from 'lucide-react'
import { PublicHeader } from '../components/PublicHeader'
import { Countdown } from '../components/Countdown'
import { api } from '../services/api'
import type { Lote } from '../types'

const DATA_EVENTO = new Date('2026-10-16T00:00:00')

const PASSOS = [
  {
    icon: Wallet,
    titulo: 'Inscreva-se',
    texto: 'Preencha seus dados no lote vigente — sem precisar criar conta.',
  },
  {
    icon: QrCode,
    titulo: 'Pague via Pix',
    texto: 'Use o Pix copia e cola gerado na hora e envie o comprovante pela página da sua inscrição.',
  },
  {
    icon: Ticket,
    titulo: 'Receba seu ingresso',
    texto: 'Depois de confirmado, seu ingresso com QR code chega por e-mail e fica disponível pra baixar.',
  },
]

export function Home() {
  const navigate = useNavigate()
  const [lote, setLote] = useState<Lote | null>(null)
  const [carregado, setCarregado] = useState(false)

  useEffect(() => {
    api
      .get<Lote | null>('/api/lotes/')
      .then((response) => setLote(response.data))
      .finally(() => setCarregado(true))
  }, [])

  return (
    <div className="min-h-screen">
      <PublicHeader />

      <section className="bg-black">
        <h1 className="sr-only">Fire Conference '26</h1>
        <img src="/HomepageFireConf.png" alt="Fire Conference '26 — Outubro 26'" className="w-full" />
      </section>

      <section className="bg-black py-12 text-center text-white">
        <div className="mx-auto max-w-3xl px-4">
          <p className="flex items-center justify-center gap-2 text-lg text-ember">
            <Calendar className="h-5 w-5" />
            16 a 18 de outubro de 2026
          </p>

          <div className="mt-10">
            <Countdown targetDate={DATA_EVENTO} />
          </div>

          <button onClick={() => navigate('/inscricao')} className="btn-primary mt-10">
            Fazer inscrição
          </button>
        </div>
      </section>

      <section className="bg-gray-50 py-16">
        <div className="mx-auto max-w-4xl px-4">
          <div className="flex items-start justify-center gap-4">
            <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-full bg-flame">
              <Calendar className="h-7 w-7 text-white" />
            </div>
            <div>
              <h2 className="mb-1 text-lg font-semibold text-flame">Data</h2>
              <p className="text-2xl font-bold text-gray-900">16 a 18 de outubro de 2026</p>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-white py-16">
        <div className="mx-auto max-w-4xl px-4">
          <h2 className="mb-10 text-center text-2xl font-bold text-gray-900 sm:text-3xl">Como funciona</h2>
          <div className="grid gap-8 sm:grid-cols-3">
            {PASSOS.map(({ icon: Icon, titulo, texto }) => (
              <div key={titulo} className="text-center">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-flame/10">
                  <Icon className="h-7 w-7 text-flame" />
                </div>
                <h3 className="mb-1 font-semibold text-gray-900">{titulo}</h3>
                <p className="text-sm text-gray-600">{texto}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {carregado && (
        <section id="inscricao" className="bg-gray-50 py-16">
          <div className="mx-auto max-w-md px-4">
            <div className="mb-12 text-center">
              <h2 className="mb-4 text-3xl font-bold text-gray-900">Valores e inscrição</h2>
              <p className="text-lg text-gray-600">
                {lote ? 'Lote vigente — garanta sua vaga.' : 'Nenhum lote disponível no momento.'}
              </p>
            </div>

            {lote ? (
              <div className="card border-2 border-flame text-center">
                <div className="mb-4 inline-block rounded-full bg-ember px-4 py-1 text-sm font-semibold text-black">
                  Lote vigente
                </div>
                <h3 className="mb-2 text-2xl font-bold text-gray-900">{lote.nome}</h3>
                <div className="mb-4 text-4xl font-bold text-flame">R$ {lote.preco}</div>
                <p className="mb-6 text-sm text-gray-600">{lote.vagas_restantes} vaga(s) restante(s)</p>
                <button onClick={() => navigate('/inscricao')} className="btn-primary w-full">
                  Inscrever-se
                </button>
              </div>
            ) : (
              <div className="card border-2 border-gray-200 text-center text-gray-600">
                As inscrições estão fechadas no momento. Volte em breve.
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  )
}
