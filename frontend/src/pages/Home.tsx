import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Calendar, Flame, QrCode, Ticket, Wallet } from 'lucide-react'
import { PublicHeader } from '../components/PublicHeader'
import { Countdown } from '../components/Countdown'
import { api } from '../services/api'
import type { Lote } from '../types'

const DATA_EVENTO = new Date('2026-10-16T00:00:00')

const PASSOS = [
  {
    icon: Wallet,
    titulo: 'Escolha seu lote',
    texto: 'Selecione um lote disponível e preencha seus dados — sem precisar criar conta.',
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
  const [lotes, setLotes] = useState<Lote[]>([])

  useEffect(() => {
    api.get<Lote[]>('/api/lotes/').then((response) => setLotes(response.data))
  }, [])

  const menorPreco = lotes.length > 0 ? Math.min(...lotes.map((lote) => Number(lote.preco))) : null

  return (
    <div className="min-h-screen">
      <PublicHeader />

      <section className="relative bg-gradient-to-br from-black to-flame-dark py-20 text-center text-white">
        <div className="mx-auto max-w-3xl px-4">
          <Flame className="mx-auto mb-4 h-14 w-14 text-ember" />
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-6xl">Fire Conference '26</h1>
          <p className="mt-4 flex items-center justify-center gap-2 text-lg text-ember">
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

      {lotes.length > 0 && (
        <section id="inscricao" className="bg-gray-50 py-16">
          <div className="mx-auto max-w-5xl px-4">
            <div className="mb-12 text-center">
              <h2 className="mb-4 text-3xl font-bold text-gray-900">Valores e inscrição</h2>
              <p className="text-lg text-gray-600">Escolha o lote e garanta sua vaga.</p>
            </div>

            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {lotes.map((lote) => {
                const esgotado = lote.vagas_restantes <= 0
                const melhorPreco = !esgotado && Number(lote.preco) === menorPreco
                return (
                  <div key={lote.id} className="card border-2 border-flame text-center">
                    {melhorPreco && (
                      <div className="mb-4 inline-block rounded-full bg-ember px-4 py-1 text-sm font-semibold text-black">
                        Melhor preço
                      </div>
                    )}
                    <h3 className="mb-2 text-2xl font-bold text-gray-900">{lote.nome}</h3>
                    <div className="mb-4 text-4xl font-bold text-flame">R$ {lote.preco}</div>
                    <p className="mb-6 text-sm text-gray-600">
                      {esgotado ? 'Vagas esgotadas' : `${lote.vagas_restantes} vaga(s) restante(s)`}
                    </p>
                    <button
                      onClick={() => navigate(`/inscricao?lote=${lote.id}`)}
                      disabled={esgotado}
                      className="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {esgotado ? 'Esgotado' : 'Inscrever-se'}
                    </button>
                  </div>
                )
              })}
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
