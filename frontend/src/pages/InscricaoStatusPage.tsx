import { useEffect, useState, type ChangeEvent } from 'react'
import { useParams } from 'react-router-dom'
import { AlertCircle, Check, Copy, Download, Upload } from 'lucide-react'
import { PublicHeader } from '../components/PublicHeader'
import { api, formatApiErrors } from '../services/api'
import type { InscricaoStatus } from '../types'

const STATUS_LABEL: Record<InscricaoStatus['status'], string> = {
  pendente: 'Pendente',
  comprovante_enviado: 'Comprovante enviado',
  confirmada: 'Confirmada',
  rejeitada: 'Rejeitada',
}

const STATUS_BADGE: Record<InscricaoStatus['status'], string> = {
  pendente: 'bg-ember/15 text-ember-dark',
  comprovante_enviado: 'bg-blue-100 text-blue-700',
  confirmada: 'bg-green-100 text-green-700',
  rejeitada: 'bg-red-100 text-red-700',
}

export function InscricaoStatusPage() {
  const { token } = useParams<{ token: string }>()
  const [inscricao, setInscricao] = useState<InscricaoStatus | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [copiado, setCopiado] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [uploadErrors, setUploadErrors] = useState<string[]>([])

  async function copiarPayload() {
    if (!inscricao) return
    try {
      await navigator.clipboard.writeText(inscricao.pix_payload)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    } catch {
      // Sem permissão de clipboard: o texto já está selecionável na caixa acima.
    }
  }

  async function enviarComprovante(event: ChangeEvent<HTMLInputElement>) {
    const arquivo = event.target.files?.[0]
    if (!arquivo) return

    setUploadErrors([])
    setEnviando(true)

    const dados = new FormData()
    dados.append('arquivo', arquivo)

    try {
      const response = await api.post<InscricaoStatus>(`/api/inscricoes/${token}/comprovante/`, dados)
      setInscricao(response.data)
    } catch (error: unknown) {
      const data = (error as { response?: { data?: unknown } })?.response?.data
      setUploadErrors(formatApiErrors(data))
    } finally {
      setEnviando(false)
      event.target.value = ''
    }
  }

  useEffect(() => {
    api
      .get<InscricaoStatus>(`/api/inscricoes/${token}/`)
      .then((response) => setInscricao(response.data))
      .catch(() => setNotFound(true))
  }, [token])

  if (notFound) {
    return (
      <div className="min-h-screen">
        <PublicHeader />
        <main className="mx-auto max-w-3xl px-4 py-10 text-center text-gray-600">Inscrição não encontrada.</main>
      </div>
    )
  }

  if (!inscricao) {
    return (
      <div className="min-h-screen">
        <PublicHeader />
        <main className="mx-auto max-w-3xl px-4 py-10 text-center text-gray-600">Carregando...</main>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <PublicHeader />

      <main className="mx-auto max-w-3xl px-4 py-10 space-y-6">
        <div className="card">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="text-xl font-bold text-gray-900">{inscricao.nome_completo}</h1>
              <p className="mt-1 text-sm text-gray-600">
                {inscricao.lote}
                {inscricao.cupom && ` · Cupom: ${inscricao.cupom}`}
              </p>
            </div>
            <span
              className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${STATUS_BADGE[inscricao.status]}`}
            >
              {STATUS_LABEL[inscricao.status]}
            </span>
          </div>
          <p className="mt-4 text-2xl font-bold text-gray-900">R$ {inscricao.preco_final}</p>
          {inscricao.status === 'rejeitada' && (
            <div className="mt-4 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
              <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
              <p className="text-sm text-red-800">{inscricao.motivo_rejeicao}</p>
            </div>
          )}
        </div>

        <div className="card">
          <h2 className="mb-3 text-lg font-bold text-gray-900">Pagamento via Pix</h2>
          <img
            src={`${import.meta.env.VITE_API_URL}/api/inscricoes/${token}/pix-qr/`}
            alt="QR code Pix"
            width={200}
            height={200}
            className="mx-auto mb-4 rounded-lg border border-gray-200"
          />
          <textarea
            readOnly
            value={inscricao.pix_payload}
            rows={3}
            className="w-full rounded-lg border border-gray-300 bg-gray-50 p-3 font-mono text-xs text-gray-700"
          />
          <button
            type="button"
            onClick={copiarPayload}
            className="btn-secondary mt-3 inline-flex items-center gap-2"
          >
            {copiado ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            {copiado ? 'Copiado!' : 'Copiar código Pix'}
          </button>
        </div>

        {inscricao.status === 'confirmada' && (
          <div className="card">
            <h2 className="mb-3 text-lg font-bold text-gray-900">Ingresso</h2>
            <a
              href={`${import.meta.env.VITE_API_URL}/api/inscricoes/${token}/ingresso/`}
              className="btn-primary inline-flex items-center gap-2"
            >
              <Download className="h-4 w-4" />
              Baixar ingresso (PDF)
            </a>
            <p className="mt-4 text-sm text-gray-600">
              Código manual para o check-in (caso a câmera não leia o QR):{' '}
              <span className="font-mono font-bold text-gray-900">{inscricao.codigo_checkin}</span>
            </p>
          </div>
        )}

        {inscricao.status === 'pendente' && (
          <div className="card">
            <h2 className="mb-3 text-lg font-bold text-gray-900">Comprovante de pagamento</h2>
            <p className="mb-4 text-sm text-gray-600">Anexe uma imagem ou PDF do comprovante do pagamento Pix.</p>
            <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border-2 border-dashed border-gray-300 px-4 py-6 text-sm font-medium text-gray-600 transition-colors hover:border-flame hover:text-flame">
              <Upload className="h-5 w-5" />
              {enviando ? 'Enviando...' : 'Selecionar arquivo'}
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,application/pdf"
                onChange={enviarComprovante}
                disabled={enviando}
                className="hidden"
              />
            </label>
            {uploadErrors.length > 0 && (
              <div className="mt-4 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
                <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
                <ul className="space-y-1 text-sm text-red-800">
                  {uploadErrors.map((error) => (
                    <li key={error}>{error}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
