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

export type LoteAdmin = {
  id: number
  nome: string
  preco: string
  limite_vagas: number
  ativo: boolean
  vagas_ocupadas: number
  vagas_restantes: number
  esgotado: boolean
  criado_em: string
}

export type CupomAdmin = {
  id: number
  codigo: string
  valor_desconto: string
  limite_usos: number
  usos_count: number
  esgotado: boolean
  criado_em: string
}

export type DashboardStats = {
  inscricoes: {
    confirmadas: number
    aguardando_revisao: number
    rejeitadas: number
  }
  receita: {
    confirmada: string
    pendente: string
  }
  checkin: {
    feitos: number
    confirmadas: number
  }
  lote_ativo: Lote | null
}
