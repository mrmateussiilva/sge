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
  auto_sync_ativo?: boolean
  ultimo_sync_em?: string | null
  ultimo_sync_status?: string
  cnpj_proprio: string
  is_admin: boolean
  erro?: string
}

export interface ItemImportacaoPayload {
  descricao_omie: string
  codigo_omie?: string
  quantidade: number
  unidade_omie?: string
  valor_unitario: number
  acao: 'vincular' | 'criar'
  produto_id?: number | null
  novo_produto?: {
    descricao: string
    tipo_produto: string
    unidade_medida: string
    estoque_minimo?: number | null
  }
  atualizar_custo: boolean
}

export interface ImportarNotaPayload {
  numero_nfe: string
  fornecedor_nome: string
  fornecedor_cnpj: string
  chave_nfe?: string
  ordem_compra_id?: number | null
  itens: ItemImportacaoPayload[]
}

export interface DeParaOmieItem {
  id: number
  fornecedor_cnpj: string
  fornecedor_nome: string
  codigo_produto_fornecedor: string
  descricao_produto_fornecedor: string
  produto_id: number
  produto_descricao: string
  produto_tipo: string
  produto_unidade: string
  preco_custo: number
  atualizado_em: string
}

export interface DeParaResponse {
  ok: boolean
  mapeamentos: DeParaOmieItem[]
  mapa: Record<string, DeParaOmieItem>
  total: number
}

export interface OrdemPendenteItem {
  item_id: number
  produto_id: number
  produto_descricao: string
  quantidade: number
  preco_unitario: number
  subtotal: number
}

export interface OrdemPendente {
  id: number
  status: string
  status_display: string
  fornecedor_id: number | null
  fornecedor_nome: string
  fornecedor_cnpj: string
  data_criacao: string
  total_itens: number
  valor_total: number
  observacao: string
  itens: OrdemPendenteItem[]
}

export interface OrdensPendentesResponse {
  ok: boolean
  ordens: OrdemPendente[]
  total: number
}

export interface OmieSyncResponse {
  ok: boolean
  mensagem: string
  total_notas: number
  novas_notas: number
  ultimo_sync_em: string
  ultimo_sync_status: string
}
