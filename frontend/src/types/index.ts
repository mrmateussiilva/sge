export interface Usuario {
  id: number
  username: string
  email: string
  nome_completo: string
  is_superuser: boolean
  grupos: string[]
  perfil: string
  permissoes: {
    operacional: boolean
    gestao: boolean
    admin: boolean
  }
}

export interface Alertas {
  estoque_baixo: number
  estoque_zerado: number
  ordens_pendentes: number
}

export interface MeResponse {
  ok: boolean
  user: Usuario
  alertas: Alertas
  app: {
    versao: string
    nome: string
  }
}

export interface ProdutoItem {
  id: number
  descricao: string
  quantidade: number
  quantidade_formatada: string
  estoque_minimo: number
  status_estoque: 'NORMAL' | 'BAIXO' | 'ZERADO'
  tipo_produto: string
  tipo_label: string
  fornecedor: string | null
  preco_custo: number | null
  preco_venda: number | null
  preco_custo_formatado: string
  preco_venda_formatado: string
  margem: number | null
  metros_por_rolo: number
  litros_por_vidro: number
  embalagens_estimadas: number
  tipo_tinta: string
  cor_tinta: string
  unidade_simbolo: string
}

export interface TabProduto {
  key: string
  label: string
  icon: string
  active: boolean
  count: number
  critical: boolean
}

export interface Paginacao {
  pagina_atual: number
  total_paginas: number
  total_itens: number
  tem_proxima: boolean
  tem_anterior: boolean
  itens_por_pagina: number
}

export interface ResumoProdutos {
  total_itens: number
  valor_custo: number
  valor_custo_formatado: string
  sem_custo: number
  baixos: number
  zerados: number
}

export interface ProdutosResponse {
  ok: boolean
  itens: ProdutoItem[]
  paginacao: Paginacao
  resumo: ResumoProdutos
  abas: TabProduto[]
  filtros_aplicados: Record<string, string>
}

export interface MovimentacaoItem {
  id: number
  produto_id: number
  produto_descricao: string
  produto_unidade: string
  tipo: 'ENTRADA' | 'SAIDA'
  tipo_display: string
  motivo: string
  motivo_display: string
  quantidade: number
  quantidade_formatada: string
  usuario: string
  data: string
  data_formatada: string
  observacao: string
}

export interface OrdemCompraItem {
  id: number
  fornecedor: { id: number; nome: string } | null
  status: 'PENDENTE' | 'APROVADA' | 'RECEBIDA' | 'CANCELADA'
  status_display: string
  data_criacao: string
  data_criacao_formatada: string
  observacao: string
  total_itens: number
  valor_total: number
  valor_total_formatado: string
}

export interface CategoriaItem {
  id: number
  nome: string
  descricao: string
  cor: string
  total_produtos: number
}

export interface FornecedorItem {
  id: number
  nome: string
  cnpj: string
  email: string
  telefone: string
  observacao: string
  total_produtos: number
}

export interface DashboardResumo {
  total_itens: number
  estoque_zerado: number
  estoque_baixo: number
  valor_total: number
  valor_total_formatado: string
  produtos_sem_custo: number
  calculo_completo: boolean
}

export interface DashboardResponse {
  ok: boolean
  resumo: DashboardResumo
  itens_criticos: Array<{
    id: number
    descricao: string
    fornecedor: string
    quantidade: number
    quantidade_formatada: string
    estoque_minimo: number | null
    estoque_minimo_formatado?: string
    status_estoque: string
    unidade_simbolo: string
  }>
  ultimas_movimentacoes: MovimentacaoItem[]
  ultimos_logs: Array<{
    id: number
    data: string
    data_formatada: string
    usuario: string
    acao: string
    descricao: string
    modelo: string
    objeto_id: number | null
  }>
}
