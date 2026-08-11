import { useEffect, useState, type ChangeEvent } from 'react'
import { useParams } from 'react-router-dom'
import { api, formatApiErrors } from '../services/api'
import type { InscricaoStatus } from '../types'

const STATUS_LABEL: Record<InscricaoStatus['status'], string> = {
  pendente: 'Pendente',
  comprovante_enviado: 'Comprovante enviado',
  confirmada: 'Confirmada',
  rejeitada: 'Rejeitada',
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
    return <p>Inscrição não encontrada.</p>
  }

  if (!inscricao) {
    return <p>Carregando...</p>
  }

  return (
    <>
      <h1>Sua inscrição</h1>
      <p>Nome: {inscricao.nome_completo}</p>
      <p>Lote: {inscricao.lote}</p>
      {inscricao.cupom && <p>Cupom: {inscricao.cupom}</p>}
      <p>Valor: R$ {inscricao.preco_final}</p>
      <p>Status: {STATUS_LABEL[inscricao.status]}</p>

      <h2>Pix copia e cola</h2>
      <textarea readOnly value={inscricao.pix_payload} rows={4} />
      <button type="button" onClick={copiarPayload}>
        {copiado ? 'Copiado!' : 'Copiar código Pix'}
      </button>

      {inscricao.status === 'pendente' && (
        <>
          <h2>Comprovante de pagamento</h2>
          <p>Anexe uma imagem ou PDF do comprovante do pagamento Pix.</p>
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp,application/pdf"
            onChange={enviarComprovante}
            disabled={enviando}
          />
          {enviando && <p>Enviando...</p>}
          {uploadErrors.length > 0 && (
            <ul>
              {uploadErrors.map((error) => (
                <li key={error}>{error}</li>
              ))}
            </ul>
          )}
        </>
      )}
    </>
  )
}
