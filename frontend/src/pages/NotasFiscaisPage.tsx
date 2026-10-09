import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  FileText,
  DollarSign,
  Truck,
  TrendingUp,
  Search,
  RefreshCw,
  Copy,
  ChevronDown,
  ChevronUp,
  Check,
  Download,
  KeyRound,
  Package,
  Calendar,
  AlertCircle,
  BarChart3,
  CalendarDays,
} from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { useDebounce } from '@/hooks/useDebounce'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { OmieConfigModal } from '@/components/omie/OmieConfigModal'
import { OmieImportarModal } from '@/components/omie/OmieImportarModal'
import type { OmieNotasResponse, NotaOmie } from '@/types'

const PERIODOS_OPCOES = [
  { dias: 7, label: '7 dias' },
  { dias: 15, label: '15 dias' },
  { dias: 30, label: '30 dias' },
  { dias: 60, label: '60 dias' },
  { dias: 90, label: '90 dias' },
  { dias: 0, label: 'Personalizado' },
]

function formatarMoeda(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return 'R$ 0,00'
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val)
}

function formatarCNPJ(cnpj: string): string {
  if (!cnpj) return ''
  const limpo = cnpj.replace(/\D/g, '')
  if (limpo.length === 14) {
    return limpo.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5')
  }
  return cnpj
}

export function NotasFiscaisPage() {
  const [diasSelecionados, setDiasSelecionados] = useState(30)
  const [dataInicio, setDataInicio] = useState('')
  const [dataFim, setDataFim] = useState('')
  const [busca, setBusca] = useState('')
  const [abaAtiva, setAbaAtiva] = useState<'lista' | 'graficos'>('lista')
  const [notasExpandidas, setNotasExpandidas] = useState<Record<number, boolean>>({})
  const [chaveCopiada, setChaveCopiada] = useState<string | null>(null)
  const [modalConfigAberto, setModalConfigAberto] = useState(false)
  const [notaParaImportar, setNotaParaImportar] = useState<NotaOmie | null>(null)

  const debouncedBusca = useDebounce(busca, 350)

  // Query de dados da Omie
  const {
    data,
    isLoading,
    isFetching,
    error,
    refetch,
  } = useQuery({
    queryKey: ['omie-notas', diasSelecionados, dataInicio, dataFim, debouncedBusca],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (diasSelecionados > 0) {
        params.append('dias', String(diasSelecionados))
      } else {
        if (dataInicio) params.append('data_inicio', dataInicio)
        if (dataFim) params.append('data_fim', dataFim)
      }
      if (debouncedBusca.trim()) {
        params.append('q', debouncedBusca.trim())
      }
      return api.get<OmieNotasResponse>(`/api/v1/omie/notas/?${params.toString()}`)
    },
    placeholderData: (previousData) => previousData,
  })

  const notas = data?.notas || []
  const kpis = data?.kpis || { total_notas: 0, valor_total: 0, fornecedores_ativos: 0, ticket_medio: 0 }
  const topFornecedores = data?.top_fornecedores || []
  const timeline = data?.timeline || []

  const toggleExpansao = (id: number) => {
    setNotasExpandidas((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const copiarChave = (chave: string) => {
    if (!chave) return
    navigator.clipboard.writeText(chave)
    setChaveCopiada(chave)
    toast.success('Chave de acesso copiada!')
    setTimeout(() => setChaveCopiada(null), 2500)
  }

  const exportarCSV = () => {
    if (notas.length === 0) {
      toast.error('Nenhuma nota disponível para exportar.')
      return
    }

    const cabecalho = [
      'Número NF-e',
      'Série',
      'Data Emissão',
      'Fornecedor',
      'Razão Social',
      'CNPJ',
      'Valor Total (R$)',
      'Etapa Omie',
      'Chave de Acesso',
    ].join(';')

    const linhas = notas.map((n) =>
      [
        `"${n.numero_nfe || ''}"`,
        `"${n.serie || ''}"`,
        `"${n.data_emissao || ''}"`,
        `"${(n.fornecedor_nome || '').replace(/"/g, '""')}"`,
        `"${(n.fornecedor_razao || '').replace(/"/g, '""')}"`,
        `"${n.fornecedor_cnpj || ''}"`,
        `"${(n.valor_total || 0).toFixed(2).replace('.', ',')}"`,
        `"${n.etapa || ''}"`,
        `"${n.chave_nfe || ''}"`,
      ].join(';')
    )

    const conteudoCSV = '\uFEFF' + [cabecalho, ...linhas].join('\r\n')
    const blob = new Blob([conteudoCSV], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `notas_fornecedores_omie_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    toast.success('Exportação CSV gerada com sucesso!')
  }

  // Valores máximos para escala dos gráficos
  const maxVolumeDiario = data?.timeline && data.timeline.length > 0
    ? Math.max(...data.timeline.map((t) => t.total), 1)
    : 1

  const maxTopFornecedor = data?.top_fornecedores && data.top_fornecedores.length > 0
    ? Math.max(...data.top_fornecedores.map((f) => f.total), 1)
    : 1

  return (
    <div className="space-y-6 pb-12">
      {/* Cabeçalho da Página */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <FileText className="w-6 h-6 text-primary" />
            Notas Fiscais de Entrada
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Notas de fornecedores (NF-e Modelo 55) sincronizadas automaticamente da Omie e SEFAZ.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setModalConfigAberto(true)}
            className="gap-1.5"
          >
            <KeyRound className="w-4 h-4 text-muted-foreground" />
            Configurar Omie
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={exportarCSV}
            disabled={notas.length === 0}
            className="gap-1.5"
          >
            <Download className="w-4 h-4" />
            Exportar CSV
          </Button>

          <Button
            variant="default"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            className="gap-1.5"
          >
            <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
            Sincronizar
          </Button>
        </div>
      </div>

      {/* Alerta de Erro caso a API falhe */}
      {error && (
        <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold">Erro ao consultar a API da Omie</p>
            <p className="text-xs text-destructive/80">
              {(error as any)?.message || 'Verifique se as credenciais do aplicativo Omie estão corretas.'}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setModalConfigAberto(true)}
              className="mt-2 text-xs h-7"
            >
              Abrir Configurações
            </Button>
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-card border-border/80 shadow-xs hover:border-border transition-all">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Total de NF-e
              </p>
              <h3 className="text-2xl font-bold text-foreground mt-1">
                {kpis.total_notas}
              </h3>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                No período selecionado
              </p>
            </div>
            <div className="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
              <FileText className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card border-border/80 shadow-xs hover:border-border transition-all">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Volume Comprado
              </p>
              <h3 className="text-2xl font-bold text-emerald-500 mt-1">
                {formatarMoeda(kpis.valor_total)}
              </h3>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Total de insumos e matérias-primas
              </p>
            </div>
            <div className="w-11 h-11 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-500">
              <DollarSign className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card border-border/80 shadow-xs hover:border-border transition-all">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Fornecedores Ativos
              </p>
              <h3 className="text-2xl font-bold text-cyan-500 mt-1">
                {kpis.fornecedores_ativos}
              </h3>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Emitentes com notas no período
              </p>
            </div>
            <div className="w-11 h-11 rounded-xl bg-cyan-500/10 flex items-center justify-center text-cyan-500">
              <Truck className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card border-border/80 shadow-xs hover:border-border transition-all">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Ticket Médio / NF
              </p>
              <h3 className="text-2xl font-bold text-amber-500 mt-1">
                {formatarMoeda(kpis.ticket_medio)}
              </h3>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Média por documento fiscal
              </p>
            </div>
            <div className="w-11 h-11 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-500">
              <TrendingUp className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Barra de Filtros e Busca */}
      <Card className="border-border/80">
        <CardContent className="p-4 space-y-3">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
            {/* Seletor de Período em Pills */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs font-medium text-muted-foreground mr-1 flex items-center gap-1">
                <CalendarDays className="w-3.5 h-3.5" />
                Período:
              </span>
              {PERIODOS_OPCOES.map((p) => {
                const ativo = diasSelecionados === p.dias
                return (
                  <button
                    key={p.label}
                    onClick={() => setDiasSelecionados(p.dias)}
                    className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                      ativo
                        ? 'bg-primary text-primary-foreground shadow-xs'
                        : 'bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {p.label}
                  </button>
                )
              })}
            </div>

            {/* Alternador de Visualização (Lista vs Gráficos) */}
            <div className="flex items-center gap-1 bg-muted/60 p-0.5 rounded-lg border border-border/60 self-start lg:self-auto">
              <button
                onClick={() => setAbaAtiva('lista')}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                  abaAtiva === 'lista'
                    ? 'bg-background text-foreground shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Lista de Notas ({notas.length})
              </button>
              <button
                onClick={() => setAbaAtiva('graficos')}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 ${
                  abaAtiva === 'graficos'
                    ? 'bg-background text-foreground shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                Análise Gráfica
              </button>
            </div>
          </div>

          {/* Datas personalizadas se selecionado */}
          {diasSelecionados === 0 && (
            <div className="pt-2 border-t border-border flex items-center gap-3 flex-wrap text-xs">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">De:</span>
                <Input
                  type="date"
                  value={dataInicio}
                  onChange={(e) => setDataInicio(e.target.value)}
                  className="w-40 h-8 text-xs"
                />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Até:</span>
                <Input
                  type="date"
                  value={dataFim}
                  onChange={(e) => setDataFim(e.target.value)}
                  className="w-40 h-8 text-xs"
                />
              </div>
            </div>
          )}

          {/* Campo de Busca Rápida */}
          <div className="relative pt-1">
            <Search className="w-4 h-4 absolute left-3 top-3.5 text-muted-foreground pointer-events-none" />
            <Input
              type="text"
              placeholder="Buscar por Fornecedor, Razão Social, CNPJ, Número da NF-e, Chave de Acesso ou Produto..."
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="pl-9 pr-8 text-sm h-10"
            />
            {busca && (
              <button
                onClick={() => setBusca('')}
                className="absolute right-3 top-3 text-xs text-muted-foreground hover:text-foreground"
              >
                ✕
              </button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Conteúdo Principal: Aba Lista ou Gráficos */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="h-28 animate-pulse bg-muted/40" />
          ))}
        </div>
      ) : abaAtiva === 'graficos' ? (
        /* ABA GRÁFICOS & ANÁLISE */
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Top Fornecedores */}
          <Card>
            <CardContent className="p-6">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2 mb-4">
                <Truck className="w-4 h-4 text-primary" />
                Top Fornecedores por Valor Total
              </h3>

              {topFornecedores.length === 0 ? (
                <p className="text-xs text-muted-foreground py-8 text-center">
                  Sem movimentações no período.
                </p>
              ) : (
                <div className="space-y-4">
                  {topFornecedores.map((f, idx) => {
                    const perc = Math.round((f.total / maxTopFornecedor) * 100)
                    return (
                      <div key={f.nome} className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-medium text-foreground truncate max-w-[260px]">
                            {idx + 1}. {f.nome}
                          </span>
                          <span className="font-bold text-foreground">
                            {formatarMoeda(f.total)}
                          </span>
                        </div>
                        <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                          <div
                            className="bg-primary h-full rounded-full transition-all duration-500"
                            style={{ width: `${Math.max(perc, 3)}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Timeline Diária de Compras */}
          <Card>
            <CardContent className="p-6">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2 mb-4">
                <Calendar className="w-4 h-4 text-cyan-500" />
                Evolução Diária de Compras (R$)
              </h3>

              {timeline.length === 0 ? (
                <p className="text-xs text-muted-foreground py-8 text-center">
                  Sem movimentações no período.
                </p>
              ) : (
                <div className="h-60 flex items-end gap-2 pt-6 pb-2 border-b border-border overflow-x-auto">
                  {timeline.map((p) => {
                    const altura = Math.round((p.total / maxVolumeDiario) * 100)
                    return (
                      <div
                        key={p.data}
                        className="flex-1 min-w-[36px] flex flex-col items-center h-full justify-end group relative"
                      >
                        {/* Tooltip */}
                        <div className="absolute -top-10 opacity-0 group-hover:opacity-100 transition-opacity bg-popover text-popover-foreground text-[10px] py-1 px-2 rounded-md shadow-lg border border-border pointer-events-none z-20 whitespace-nowrap">
                          <p className="font-bold">{p.data}</p>
                          <p className="text-cyan-400 font-semibold">{formatarMoeda(p.total)}</p>
                        </div>

                        {/* Barra */}
                        <div
                          style={{ height: `${Math.max(altura, 4)}%` }}
                          className="w-full bg-cyan-500 hover:bg-cyan-400 rounded-t-sm transition-all duration-300"
                        />
                        <span className="text-[10px] text-muted-foreground mt-2 truncate max-w-full">
                          {p.data.slice(0, 5)}
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      ) : (
        /* ABA LISTA DE NOTAS */
        <div className="space-y-3">
          {notas.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="py-12 text-center space-y-3">
                <Package className="w-10 h-10 text-muted-foreground/60 mx-auto" />
                <h3 className="text-base font-semibold text-foreground">
                  Nenhuma nota fiscal encontrada
                </h3>
                <p className="text-xs text-muted-foreground max-w-md mx-auto">
                  {busca
                    ? 'Nenhum resultado corresponde aos termos da pesquisa. Tente buscar por outros termos ou limpe o filtro.'
                    : 'Não foram encontradas NF-e Modelo 55 para o período selecionado.'}
                </p>
                {busca && (
                  <Button variant="outline" size="sm" onClick={() => setBusca('')}>
                    Limpar pesquisa
                  </Button>
                )}
              </CardContent>
            </Card>
          ) : (
            notas.map((nota) => {
              const expandida = Boolean(notasExpandidas[nota.id_receb])
              const temItens = nota.itens && nota.itens.length > 0
              const temParcelas = nota.parcelas && nota.parcelas.length > 0

              return (
                <Card
                  key={nota.id_receb || nota.chave_nfe}
                  className="border-border/80 hover:border-primary/40 transition-colors"
                >
                  <CardContent className="p-4 sm:p-5 space-y-4">
                    {/* Linha Principal do Cabeçalho da Nota */}
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                      {/* Identificação Fornecedor & NF */}
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-base font-bold text-foreground">
                            NF-e nº {nota.numero_nfe || 'S/N'}
                          </span>
                          {nota.serie && (
                            <Badge variant="outline" className="text-[10px] py-0">
                              Série {nota.serie}
                            </Badge>
                          )}
                          <Badge variant="secondary" className="text-[10px] py-0 bg-primary/10 text-primary">
                            Modelo 55
                          </Badge>
                          {nota.ja_importada && (
                            <Badge variant="success" className="text-[10px] py-0">
                              Importada no SGE
                            </Badge>
                          )}
                        </div>

                        <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
                          <span className="font-semibold text-foreground">
                            {nota.fornecedor_nome || nota.fornecedor_razao || 'Fornecedor não identificado'}
                          </span>
                          {nota.fornecedor_razao && nota.fornecedor_razao !== nota.fornecedor_nome && (
                            <span className="text-muted-foreground hidden sm:inline">
                              ({nota.fornecedor_razao})
                            </span>
                          )}
                          {nota.fornecedor_cnpj && (
                            <span className="font-mono text-muted-foreground">
                              • CNPJ: {formatarCNPJ(nota.fornecedor_cnpj)}
                            </span>
                          )}
                          <span className="text-muted-foreground">
                            • Emissão: <strong className="text-foreground">{nota.data_emissao}</strong>
                          </span>
                        </div>
                      </div>

                      {/* Valor Total & Ações Rápidas */}
                      <div className="flex items-center justify-between md:justify-end gap-3 shrink-0 pt-2 md:pt-0 border-t md:border-t-0 border-border">
                        <div className="text-left md:text-right">
                          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                            Valor Total
                          </p>
                          <p className="text-lg font-extrabold text-primary">
                            {formatarMoeda(nota.valor_total)}
                          </p>
                        </div>

                        <div className="flex items-center gap-1.5 flex-wrap">
                          {/* Botão Importar p/ Estoque */}
                          {!nota.ja_importada && temItens && (
                            <Button
                              size="sm"
                              onClick={() => setNotaParaImportar(nota)}
                              className="h-8 text-xs gap-1.5 bg-primary hover:bg-primary/90 text-primary-foreground font-semibold shadow-xs"
                            >
                              <Package className="w-3.5 h-3.5" />
                              Importar p/ Estoque
                            </Button>
                          )}

                          {/* Botão Copiar Chave */}
                          <button
                            onClick={() => copiarChave(nota.chave_nfe)}
                            title="Copiar Chave de Acesso (44 dígitos)"
                            className="p-2 rounded-lg border border-border hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                          >
                            {chaveCopiada === nota.chave_nfe ? (
                              <Check className="w-4 h-4 text-emerald-500" />
                            ) : (
                              <Copy className="w-4 h-4" />
                            )}
                          </button>

                          {/* Botão Expandir / Recolher */}
                          <button
                            onClick={() => toggleExpansao(nota.id_receb)}
                            className="flex items-center gap-1 px-3 py-2 rounded-lg border border-border hover:bg-muted text-xs font-medium text-foreground transition-colors"
                          >
                            <span>{temItens ? `${nota.itens.length} itens` : 'Detalhes'}</span>
                            {expandida ? (
                              <ChevronUp className="w-3.5 h-3.5 text-muted-foreground" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
                            )}
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Detalhes Expansíveis */}
                    {expandida && (
                      <div className="pt-4 border-t border-border space-y-4 animate-in fade-in-50 duration-200">
                        {/* Banner de Ação de Importação se não importada */}
                        {!nota.ja_importada && temItens && (
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-xl bg-primary/5 border border-primary/20">
                            <div className="flex items-center gap-2">
                              <Package className="w-4 h-4 text-primary shrink-0" />
                              <span className="text-xs text-foreground">
                                Esta nota possui <strong>{nota.itens.length}</strong> produto(s) faturados. Você pode mesclá-los com produtos existentes ou cadastrar novos insumos.
                              </span>
                            </div>
                            <Button
                              size="sm"
                              onClick={() => setNotaParaImportar(nota)}
                              className="h-7 text-xs gap-1.5 shrink-0"
                            >
                              <Package className="w-3 h-3" />
                              Importar & Conciliar Itens
                            </Button>
                          </div>
                        )}
                        {/* Chave de Acesso em Bloco Monospace */}
                        {nota.chave_nfe && (
                          <div className="p-2.5 rounded-lg bg-muted/40 border border-border flex items-center justify-between gap-3 text-xs">
                            <div className="truncate">
                              <span className="font-semibold text-muted-foreground mr-2">Chave SEFAZ:</span>
                              <code className="font-mono text-foreground tracking-tight select-all">
                                {nota.chave_nfe}
                              </code>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => copiarChave(nota.chave_nfe)}
                              className="h-6 text-[11px] gap-1 shrink-0"
                            >
                              <Copy className="w-3 h-3" />
                              Copiar
                            </Button>
                          </div>
                        )}

                        {/* Tabela de Produtos / Itens da NF */}
                        {temItens ? (
                          <div className="space-y-2">
                            <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                              <Package className="w-3.5 h-3.5 text-primary" />
                              Itens da Nota ({nota.itens.length})
                            </h4>

                            <div className="border border-border rounded-xl overflow-hidden overflow-x-auto">
                              <table className="w-full text-xs text-left">
                                <thead className="bg-muted/60 text-muted-foreground border-b border-border">
                                  <tr>
                                    <th className="py-2.5 px-3 font-semibold">Código</th>
                                    <th className="py-2.5 px-3 font-semibold">Descrição do Insumo / Produto</th>
                                    <th className="py-2.5 px-2 font-semibold">NCM</th>
                                    <th className="py-2.5 px-2 font-semibold">CFOP</th>
                                    <th className="py-2.5 px-3 font-semibold text-right">Qtd</th>
                                    <th className="py-2.5 px-2 font-semibold">UN</th>
                                    <th className="py-2.5 px-3 font-semibold text-right">Preço Unit.</th>
                                    <th className="py-2.5 px-3 font-semibold text-right">Total Item</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-border">
                                  {nota.itens.map((it, idx) => (
                                    <tr
                                      key={`${it.codigo_produto}-${idx}`}
                                      className="hover:bg-muted/30 transition-colors"
                                    >
                                      <td className="py-2 px-3 font-mono text-muted-foreground">
                                        {it.codigo_produto || '-'}
                                      </td>
                                      <td className="py-2 px-3 font-medium text-foreground max-w-[280px] truncate">
                                        {it.descricao || 'Item sem descrição'}
                                      </td>
                                      <td className="py-2 px-2 font-mono text-muted-foreground">
                                        {it.ncm || '-'}
                                      </td>
                                      <td className="py-2 px-2 font-mono text-muted-foreground">
                                        {it.cfop || '-'}
                                      </td>
                                      <td className="py-2 px-3 text-right font-semibold text-foreground">
                                        {it.quantidade}
                                      </td>
                                      <td className="py-2 px-2 text-muted-foreground">
                                        {it.unidade || 'UN'}
                                      </td>
                                      <td className="py-2 px-3 text-right text-muted-foreground">
                                        {formatarMoeda(it.preco_unitario)}
                                      </td>
                                      <td className="py-2 px-3 text-right font-bold text-foreground">
                                        {formatarMoeda(it.valor_total)}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        ) : (
                          <p className="text-xs text-muted-foreground py-2 italic">
                            Detalhes dos produtos não retornados pela Omie nesta consulta.
                          </p>
                        )}

                        {/* Condições de Pagamento / Parcelas */}
                        {temParcelas && (
                          <div className="space-y-2 pt-1">
                            <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                              <Calendar className="w-3.5 h-3.5 text-cyan-500" />
                              Vencimentos & Parcelas ({nota.parcelas.length})
                            </h4>

                            <div className="flex items-center gap-2 flex-wrap">
                              {nota.parcelas.map((p) => (
                                <div
                                  key={p.sequencia}
                                  className="px-3 py-1.5 rounded-lg border border-border bg-muted/30 text-xs flex items-center gap-2"
                                >
                                  <span className="text-muted-foreground font-medium">
                                    {p.sequencia}ª:
                                  </span>
                                  <span className="text-foreground">
                                    Venc. {p.vencimento || 'A vencer'}
                                  </span>
                                  <strong className="text-primary font-bold">
                                    {formatarMoeda(p.valor)}
                                  </strong>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )
            })
          )}
        </div>
      )}

      {/* Modal de Configuração de Credenciais Omie */}
      <OmieConfigModal
        isOpen={modalConfigAberto}
        onClose={() => setModalConfigAberto(false)}
      />

      {/* Modal de Importação e Conciliação de NF-e */}
      <OmieImportarModal
        nota={notaParaImportar}
        isOpen={Boolean(notaParaImportar)}
        onClose={() => setNotaParaImportar(null)}
      />
    </div>
  )
}
