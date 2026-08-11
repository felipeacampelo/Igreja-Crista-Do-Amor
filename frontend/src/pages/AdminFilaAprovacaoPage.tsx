import { useEffect, useState } from 'react'
import { adminApi, formatApiErrors } from '../services/api'
import type { InscricaoFilaAprovacao } from '../types'

const SEXO_LABEL: Record<InscricaoFilaAprovacao['sexo'], string> = {
  F: 'Feminino',
  M: 'Masculino',
}

export function AdminFilaAprovacaoPage() {
  const [fila, setFila] = useState<InscricaoFilaAprovacao[] | null>(null)
  const [semPermissao, setSemPermissao] = useState(false)
  const [erros, setErros] = useState<Record<number, string[]>>({})
  const [rejeitando, setRejeitando] = useState<Record<number, boolean>>({})
  const [motivos, setMotivos] = useState<Record<number, string>>({})

  function carregarFila() {
    adminApi
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
      await adminApi.post(`/api/admin/inscricoes/${id}/aprovar/`)
      carregarFila()
    } catch (error: unknown) {
      const data = (error as { response?: { data?: unknown } })?.response?.data
      setErros((prev) => ({ ...prev, [id]: formatApiErrors(data) }))
    }
  }

  async function confirmarRejeicao(id: number) {
    const motivo = (motivos[id] ?? '').trim()
    if (!motivo) {
      setErros((prev) => ({ ...prev, [id]: ['Informe o motivo da rejeição.'] }))
      return
    }

    setErros((prev) => ({ ...prev, [id]: [] }))
    try {
      await adminApi.post(`/api/admin/inscricoes/${id}/rejeitar/`, { motivo })
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
          <p>Celular: {inscricao.celular}</p>
          <p>Sexo: {SEXO_LABEL[inscricao.sexo]}</p>
          <p>Data de nascimento: {inscricao.data_nascimento}</p>
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
          <button
            type="button"
            onClick={() => setRejeitando((prev) => ({ ...prev, [inscricao.id]: true }))}
          >
            Rejeitar
          </button>

          {rejeitando[inscricao.id] && (
            <div>
              <label>
                Motivo da rejeição
                <input
                  value={motivos[inscricao.id] ?? ''}
                  onChange={(e) => setMotivos((prev) => ({ ...prev, [inscricao.id]: e.target.value }))}
                />
              </label>
              <button type="button" onClick={() => confirmarRejeicao(inscricao.id)}>
                Confirmar rejeição
              </button>
            </div>
          )}

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
