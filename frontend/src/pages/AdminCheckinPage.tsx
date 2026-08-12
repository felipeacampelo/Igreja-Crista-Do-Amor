import { useState } from 'react'
import { adminApi } from '../services/api'
import { useQrScanner } from '../hooks/useQrScanner'
import type { CheckinResultado } from '../types'

const RESULTADO_LABEL: Record<CheckinResultado['resultado'], string> = {
  aceita: 'LIBERADO',
  duplicada: 'JÁ UTILIZADO',
  bloqueada: 'BLOQUEADO',
}

export function AdminCheckinPage() {
  const [codigo, setCodigo] = useState('')
  const [resultado, setResultado] = useState<CheckinResultado | null>(null)
  const [erro, setErro] = useState('')
  const [validando, setValidando] = useState(false)

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
    } catch {
      setErro('Erro ao validar. Tente novamente.')
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

  if (resultado) {
    return (
      <>
        <h1>{RESULTADO_LABEL[resultado.resultado]}</h1>
        {resultado.nome_completo && <p>Nome: {resultado.nome_completo}</p>}
        {resultado.lote && <p>Lote: {resultado.lote}</p>}
        <button type="button" onClick={proximo}>
          Próximo
        </button>
      </>
    )
  }

  return (
    <>
      <h1>Check-in</h1>

      <h2>Câmera</h2>
      <video ref={videoRef} muted playsInline aria-label="Câmera para leitura de QR code" />
      {!scanning ? (
        <button type="button" onClick={startCamera}>
          Iniciar leitura
        </button>
      ) : (
        <button type="button" onClick={stopCamera}>
          Parar câmera
        </button>
      )}
      {cameraError && <p>{cameraError}</p>}

      <h2>Código manual</h2>
      <label>
        Código do ingresso
        <input
          value={codigo}
          onChange={(e) => setCodigo(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') validarManual()
          }}
        />
      </label>
      <button type="button" onClick={validarManual} disabled={validando || !codigo.trim()}>
        {validando ? 'Validando...' : 'Validar ingresso'}
      </button>
      {erro && <p>{erro}</p>}
    </>
  )
}
