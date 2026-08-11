import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../services/api'
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
    </>
  )
}
