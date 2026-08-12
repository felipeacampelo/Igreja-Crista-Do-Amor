import { useState } from 'react'
import { AlertCircle, Camera, CameraOff, CheckCircle2, RotateCcw, ShieldAlert, XCircle } from 'lucide-react'
import { AdminShell } from '../components/AdminShell'
import { adminApi } from '../services/api'
import { useQrScanner } from '../hooks/useQrScanner'
import type { CheckinResultado } from '../types'

const RESULTADO_LABEL: Record<CheckinResultado['resultado'], string> = {
  aceita: 'LIBERADO',
  duplicada: 'JÁ UTILIZADO',
  bloqueada: 'BLOQUEADO',
}

const RESULTADO_STYLE: Record<CheckinResultado['resultado'], { bg: string; text: string; icon: typeof CheckCircle2 }> = {
  aceita: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle2 },
  duplicada: { bg: 'bg-ember/15', text: 'text-ember-dark', icon: ShieldAlert },
  bloqueada: { bg: 'bg-red-100', text: 'text-red-700', icon: XCircle },
}

export function AdminCheckinPage() {
  const [codigo, setCodigo] = useState('')
  const [resultado, setResultado] = useState<CheckinResultado | null>(null)
  const [erro, setErro] = useState('')
  const [validando, setValidando] = useState(false)
  const [semPermissao, setSemPermissao] = useState(false)

  const { videoRef, scanning, cameraError, startCamera, stopCamera } = useQrScanner(async (data) => {
    await validar(() => adminApi.post<CheckinResultado>('/api/admin/checkin/scan/', { token_qr: data }))
    stopCamera()
  })

  async function validar(chamada: () => Promise<{ data: CheckinResultado }>) {
    setErro('')
    setValidando(true)
    try {
      const response = await chamada()
      setResultado(response.data)
    } catch (error: unknown) {
      const statusCode = (error as { response?: { status?: number } })?.response?.status
      if (statusCode === 403 || statusCode === 401) {
        setSemPermissao(true)
      } else {
        setErro('Erro ao validar. Tente novamente.')
      }
    } finally {
      setValidando(false)
    }
  }

  async function validarManual() {
    if (!codigo.trim()) return
    await validar(() => adminApi.post<CheckinResultado>('/api/admin/checkin/manual/', { codigo: codigo.trim() }))
  }

  function proximo() {
    setResultado(null)
    setErro('')
    setCodigo('')
  }

  if (semPermissao) {
    return (
      <AdminShell>
        <p className="text-gray-600">Você não tem permissão para realizar check-in.</p>
      </AdminShell>
    )
  }

  if (resultado) {
    const estilo = RESULTADO_STYLE[resultado.resultado]
    const Icon = estilo.icon
    return (
      <AdminShell>
        <div className="mx-auto max-w-md">
          <div className={`card flex flex-col items-center text-center ${estilo.bg}`}>
            <Icon className={`h-16 w-16 ${estilo.text}`} />
            <h1 className={`mt-4 text-3xl font-extrabold tracking-wide ${estilo.text}`}>
              {RESULTADO_LABEL[resultado.resultado]}
            </h1>
            {resultado.nome_completo && (
              <p className="mt-3 text-lg font-semibold text-gray-900">{resultado.nome_completo}</p>
            )}
            {resultado.lote && <p className="text-sm text-gray-600">{resultado.lote}</p>}
            <button type="button" onClick={proximo} className="btn-primary mt-6 inline-flex items-center gap-2">
              <RotateCcw className="h-4 w-4" />
              Próximo
            </button>
          </div>
        </div>
      </AdminShell>
    )
  }

  return (
    <AdminShell>
      <div className="mx-auto max-w-md space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Check-in</h1>

        <div className="card">
          <h2 className="mb-3 text-lg font-bold text-gray-900">Câmera</h2>
          <video
            ref={videoRef}
            muted
            playsInline
            aria-label="Câmera para leitura de QR code"
            className="w-full rounded-lg bg-black"
          />
          <div className="mt-3">
            {!scanning ? (
              <button type="button" onClick={startCamera} className="btn-primary inline-flex items-center gap-2">
                <Camera className="h-4 w-4" />
                Iniciar leitura
              </button>
            ) : (
              <button type="button" onClick={stopCamera} className="btn-secondary inline-flex items-center gap-2">
                <CameraOff className="h-4 w-4" />
                Parar câmera
              </button>
            )}
          </div>
          {cameraError && (
            <div className="mt-3 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
              <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
              <p className="text-sm text-red-800">{cameraError}</p>
            </div>
          )}
        </div>

        <div className="card">
          <h2 className="mb-3 text-lg font-bold text-gray-900">Código manual</h2>
          <label className="field-label">Código do ingresso</label>
          <input
            className="field-input"
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') validarManual()
            }}
          />
          <button
            type="button"
            onClick={validarManual}
            disabled={validando || !codigo.trim()}
            className="btn-primary mt-3 w-full disabled:opacity-50"
          >
            {validando ? 'Validando...' : 'Validar ingresso'}
          </button>
          {erro && (
            <div className="mt-3 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
              <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
              <p className="text-sm text-red-800">{erro}</p>
            </div>
          )}
        </div>
      </div>
    </AdminShell>
  )
}
