export type Lote = {
  id: number
  nome: string
  preco: string
  vagas_restantes: number
}

export type InscricaoStatus = {
  nome_completo: string
  lote: string
  cupom: string | null
  status: 'pendente' | 'comprovante_enviado' | 'confirmada' | 'rejeitada'
  preco_final: string
  criado_em: string
  pix_payload: string
}
