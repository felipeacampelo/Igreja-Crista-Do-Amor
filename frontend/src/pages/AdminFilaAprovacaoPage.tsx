import { useEffect, useState } from 'react'
import { api, formatApiErrors } from '../services/api'
import type { InscricaoFilaAprovacao } from '../types'

export function AdminFilaAprovacaoPage() {
  const [fila, setFila] = useState<InscricaoFilaAprovacao[] | null>(null)
  const [semPermissao, setSemPermissao] = useState(false)
  const [erros, setErros] = useState<Record<number, string[]>>({})

  function carregarFila() {
    api
      .get<InscricaoFilaAprovacao[]>('/api/admin/inscricoes/fila-aprovacao/')
      .then((response) => setFila(response.data))
      .catch((error) => {
        if (error?.response?.status === 403 || error?.response?.status === 401) {
          setSemPermissao(true)
        }
      })
  }

  useEffect(() => {
    carregarFila()
  }, [])

  async function aprovar(id: number) {
    setErros((prev) => ({ ...prev, [id]: [] }))
    try {
      await api.post(`/api/admin/inscricoes/${id}/aprovar/`)
      carregarFila()
    } catch (error: unknown) {
      const data = (error as { response?: { data?: unknown } })?.response?.data
      setErros((prev) => ({ ...prev, [id]: formatApiErrors(data) }))
    }
  }

  async function rejeitar(id: number) {
    const motivo = window.prompt('Motivo da rejeição:')
    if (!motivo) return

    setErros((prev) => ({ ...prev, [id]: [] }))
    try {
      await api.post(`/api/admin/inscricoes/${id}/rejeitar/`, { motivo })
      carregarFila()
    } catch (error: unknown) {
      const data = (error as { response?: { data?: unknown } })?.response?.data
      setErros((prev) => ({ ...prev, [id]: formatApiErrors(data) }))
    }
  }

  if (semPermissao) {
    return <p>Você não tem permissão para acessar a fila de aprovação.</p>
  }

  if (!fila) {
    return <p>Carregando...</p>
  }

  return (
    <>
      <h1>Fila de aprovação</h1>
      {fila.length === 0 && <p>Nenhuma inscrição aguardando revisão.</p>}
      {fila.map((inscricao) => (
        <div key={inscricao.id}>
          <p>Nome: {inscricao.nome_completo}</p>
          <p>CPF: {inscricao.cpf}</p>
          <p>E-mail: {inscricao.email}</p>
          <p>Lote: {inscricao.lote}</p>
          {inscricao.cupom && <p>Cupom: {inscricao.cupom}</p>}
          <p>Valor esperado: R$ {inscricao.preco_final}</p>
          {inscricao.comprovante_url ? (
            <p>
              <a href={inscricao.comprovante_url} target="_blank" rel="noreferrer">
                Ver comprovante
              </a>
            </p>
          ) : (
            <p>Comprovante indisponível no momento.</p>
          )}
          <button type="button" onClick={() => aprovar(inscricao.id)}>
            Aprovar
          </button>
          <button type="button" onClick={() => rejeitar(inscricao.id)}>
            Rejeitar
          </button>
          {erros[inscricao.id]?.length > 0 && (
            <ul>
              {erros[inscricao.id].map((erro) => (
                <li key={erro}>{erro}</li>
              ))}
            </ul>
          )}
          <hr />
        </div>
      ))}
    </>
  )
}
