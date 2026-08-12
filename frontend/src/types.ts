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
  motivo_rejeicao: string
  codigo_checkin: string
}

export type InscricaoFilaAprovacao = {
  id: number
  nome_completo: string
  cpf: string
  email: string
  celular: string
  sexo: 'M' | 'F'
  data_nascimento: string
  lote: string
  cupom: string | null
  preco_final: string
  status: string
  comprovante_url: string | null
  criado_em: string
}

export type CheckinResultado = {
  resultado: 'aceita' | 'duplicada' | 'bloqueada'
  nome_completo: string | null
  lote: string | null
  checkin_em: string | null
}
