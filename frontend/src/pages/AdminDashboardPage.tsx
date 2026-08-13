import { useEffect, useState } from 'react'
import { CheckCircle2, Clock, DollarSign, QrCode, XCircle } from 'lucide-react'
import { AdminShell } from '../components/AdminShell'
import { adminApi } from '../services/api'
import type { DashboardStats } from '../types'

function StatCard({
  icon: Icon,
  label,
  value,
  tone = 'flame',
}: {
  icon: typeof CheckCircle2
  label: string
  value: string | number
  tone?: 'flame' | 'green' | 'ember' | 'red'
}) {
  const tons: Record<string, string> = {
    flame: 'bg-flame/10 text-flame',
    green: 'bg-green-100 text-green-700',
    ember: 'bg-ember/15 text-ember-dark',
    red: 'bg-red-100 text-red-700',
  }
  return (
    <div className="card flex items-center gap-4">
      <div className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full ${tons[tone]}`}>
        <Icon className="h-6 w-6" />
      </div>
      <div>
        <p className="text-sm text-gray-600">{label}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
      </div>
    </div>
  )
}

export function AdminDashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [semPermissao, setSemPermissao] = useState(false)

  useEffect(() => {
    adminApi
      .get<DashboardStats>('/api/admin/dashboard/')
      .then((response) => {
        setSemPermissao(false)
        setStats(response.data)
      })
      .catch((error) => {
        if (error?.response?.status === 403 || error?.response?.status === 401) {
          setSemPermissao(true)
        }
      })
  }, [])

  if (semPermissao) {
    return (
      <AdminShell>
        <p className="text-gray-600">Você não tem permissão para acessar o dashboard.</p>
      </AdminShell>
    )
  }

  if (!stats) {
    return (
      <AdminShell>
        <p className="text-gray-600">Carregando...</p>
      </AdminShell>
    )
  }

  return (
    <AdminShell>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-600">Visão geral das inscrições da Fire Conference.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard icon={CheckCircle2} label="Confirmadas" value={stats.inscricoes.confirmadas} tone="green" />
        <StatCard icon={Clock} label="Aguardando revisão" value={stats.inscricoes.aguardando_revisao} tone="ember" />
        <StatCard icon={XCircle} label="Rejeitadas" value={stats.inscricoes.rejeitadas} tone="red" />
        <StatCard icon={DollarSign} label="Receita confirmada" value={`R$ ${stats.receita.confirmada}`} tone="green" />
        <StatCard icon={DollarSign} label="Receita pendente" value={`R$ ${stats.receita.pendente}`} tone="ember" />
        <StatCard
          icon={QrCode}
          label="Check-in realizado"
          value={`${stats.checkin.feitos} / ${stats.checkin.confirmadas}`}
        />
      </div>

      <div className="mt-6 card">
        <h2 className="mb-3 text-lg font-bold text-gray-900">Lote vigente</h2>
        {stats.lote_ativo ? (
          <div className="flex items-center justify-between">
            <div>
              <p className="text-lg font-semibold text-gray-900">{stats.lote_ativo.nome}</p>
              <p className="text-sm text-gray-600">{stats.lote_ativo.vagas_restantes} vaga(s) restante(s)</p>
            </div>
            <p className="text-2xl font-bold text-flame">R$ {stats.lote_ativo.preco}</p>
          </div>
        ) : (
          <p className="text-gray-600">Nenhum lote ativo no momento.</p>
        )}
      </div>
    </AdminShell>
  )
}
