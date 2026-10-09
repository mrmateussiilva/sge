export interface ItemNotaOmie {
  codigo_produto: string
  descricao: string
  ncm: string
  cfop: string
  quantidade: number
  unidade: string
  preco_unitario: number
  valor_total: number
  id_produto?: number
  id_item?: number
}

export interface ParcelaNotaOmie {
  sequencia: number
  vencimento: string
  valor: number
}

export interface NotaOmie {
  id_receb: number
  id_fornecedor?: number
  numero_nfe: string
  serie: string
  chave_nfe: string
  data_emissao: string
  fornecedor_nome: string
  fornecedor_razao: string
  fornecedor_cnpj: string
  valor_total: number
  natureza_operacao: string
  etapa: string
  itens: ItemNotaOmie[]
  parcelas: ParcelaNotaOmie[]
  ja_importada?: boolean
  _meta?: {
    tipo_doc: string
    modelo: string
    cnpj_emitente: string
    eh_propria: boolean
    eh_fornecedor_nfe: boolean
  }
}

export interface OmieKpis {
  total_notas: number
  valor_total: number
  fornecedores_ativos: number
  ticket_medio: number
}

export interface OmiePeriodo {
  inicio: string
  fim: string
  dias: number
}

export interface TopFornecedor {
  nome: string
  total: number
}

export interface TimelinePonto {
  data: string
  total: number
}

export interface OmieNotasResponse {
  ok: boolean
  notas: NotaOmie[]
  kpis: OmieKpis
  periodo: OmiePeriodo
  top_fornecedores: TopFornecedor[]
  timeline: TimelinePonto[]
  total_sem_filtro_busca: number
  erro?: string
}

export interface OmieConfigResponse {
  ok: boolean
  configurado: boolean
  app_key_mascarada: string
  atualizado_em: string | null
  cnpj_proprio: string
  is_admin: boolean
  erro?: string
}
