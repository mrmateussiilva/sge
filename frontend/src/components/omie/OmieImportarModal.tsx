import { useState, useEffect, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Package,
  PlusCircle,
  Link2,
  CheckCircle2,
  Sparkles,
  Loader2,
  AlertCircle,
  Building,
  Calendar,
  Search,
} from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { Modal } from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import type { NotaOmie, ImportarNotaPayload, OpcoesProduto, ProdutoCompacto } from '@/types'

interface OmieImportarModalProps {
  nota: NotaOmie | null
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
}

interface ItemFormState {
  idx: number
  selecionado: boolean
  acao: 'vincular' | 'criar'
  // Dados Omie originais
  descricao_omie: string
  codigo_omie: string
  unidade_omie: string
  // Valores a importar
  quantidade: string
  valor_unitario: number
  atualizar_custo: boolean
  // Se vincular
  produto_id: number | null
  produto_busca: string
  sugestao_automatica: boolean
  // Se criar
  novo_descricao: string
  novo_tipo_produto: string
  novo_unidade_medida: string
  novo_estoque_minimo: string
}

function formatarMoeda(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return 'R$ 0,00'
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val)
}

function adivinharTipoProduto(descricao: string): string {
  const d = (descricao || '').toUpperCase()
  if (d.includes('TECIDO') || d.includes('MALHA') || d.includes('DRY FIT') || d.includes('TACTEL') || d.includes('OXFORD') || d.includes('HELANCA')) {
    return 'TECIDO'
  }
  if (d.includes('PAPEL') || d.includes('BOBINA') || d.includes('SUBLIMATICO')) {
    return 'PAPEL'
  }
  if (d.includes('TINTA') || d.includes('SOLVENTE') || d.includes('SUBLIMACAO') || d.includes('CYAN') || d.includes('MAGENTA') || d.includes('YELLOW') || d.includes('BLACK')) {
    return 'TINTA'
  }
  if (d.includes('ELASTICO') || d.includes('ZIPER') || d.includes('LINHA') || d.includes('FIO') || d.includes('BOTAO')) {
    return 'AVIAMENTO'
  }
  return 'OUTRO'
}

function adivinharUnidade(unidade: string, tipo: string): string {
  const u = (unidade || '').trim().toUpperCase()
  if (['M', 'MT', 'METRO', 'METROS'].includes(u)) return 'M'
  if (['L', 'LT', 'LITRO', 'LITROS'].includes(u)) return 'L'
  if (['KG', 'KILO', 'QUILO'].includes(u)) return 'KG'
  if (['RL', 'ROLO', 'ROLOS'].includes(u)) return 'RL'
  if (['CX', 'CAIXA'].includes(u)) return 'CX'
  if (['PC', 'PECA', 'PÇ'].includes(u)) return 'PC'
  if (['UN', 'UND', 'UNIDADE'].includes(u)) return 'UN'
  if (tipo === 'TECIDO' || tipo === 'PAPEL') return 'M'
  if (tipo === 'TINTA') return 'L'
  return 'UN'
}

export function OmieImportarModal({
  nota,
  isOpen,
  onClose,
  onSuccess,
}: OmieImportarModalProps) {
  const queryClient = useQueryClient()
  const [itensState, setItensState] = useState<ItemFormState[]>([])

  // Busca opções de produtos (tipos, unidades, lista completa de produtos)
  const { data: opcoes, isLoading: carregandoOpcoes } = useQuery<OpcoesProduto>({
    queryKey: ['produtos-opcoes'],
    queryFn: () => api.get<OpcoesProduto>('/api/v1/produtos/opcoes/'),
    enabled: isOpen,
    staleTime: 1000 * 60 * 5,
  })

  const produtosCadastrados: ProdutoCompacto[] = useMemo(() => opcoes?.produtos || [], [opcoes?.produtos])

  // Inicializa o estado dos itens ao abrir a nota e carregar produtos
  useEffect(() => {
    if (!nota || !isOpen) {
      setItensState([])
      return
    }

    const novosItens: ItemFormState[] = (nota.itens || []).map((it, idx) => {
      const descLimpa = (it.descricao || '').trim()
      const codLimpo = (it.codigo_produto || '').trim()
      const descLower = descLimpa.toLowerCase()
      const codLower = codLimpo.toLowerCase()

      // Tenta encontrar um produto correspondente no estoque (Auto-match inteligente)
      let matchEncontrado: { id: number; descricao: string } | null = null

      if (produtosCadastrados.length > 0) {
        // 1. Busca exata por código se houver
        if (codLower) {
          matchEncontrado = produtosCadastrados.find((p) =>
            p.descricao.toLowerCase().includes(codLower)
          ) || null
        }
        // 2. Busca por descrição contida ou igual
        if (!matchEncontrado && descLower) {
          matchEncontrado = produtosCadastrados.find((p) => {
            const pDesc = p.descricao.toLowerCase()
            return pDesc === descLower || pDesc.includes(descLower) || descLower.includes(pDesc)
          }) || null
        }
        // 3. Busca por palavras-chave principais (ex: 'dry fit branco')
        if (!matchEncontrado && descLower) {
          const palavras = descLower.split(/\s+/).filter((w) => w.length > 3)
          if (palavras.length >= 2) {
            matchEncontrado = produtosCadastrados.find((p) => {
              const pDesc = p.descricao.toLowerCase()
              const matches = palavras.filter((w) => pDesc.includes(w))
              return matches.length >= 2
            }) || null
          }
        }
      }

      const tipoSugerido = adivinharTipoProduto(descLimpa)
      const unidadeSugerida = adivinharUnidade(it.unidade, tipoSugerido)

      return {
        idx,
        selecionado: true,
        acao: 'vincular',
        descricao_omie: descLimpa,
        codigo_omie: codLimpo,
        unidade_omie: it.unidade || 'UN',
        quantidade: String(it.quantidade || 1),
        valor_unitario: it.preco_unitario || 0,
        atualizar_custo: true,
        produto_id: matchEncontrado ? matchEncontrado.id : null,
        produto_busca: '',
        sugestao_automatica: Boolean(matchEncontrado),
        novo_descricao: descLimpa,
        novo_tipo_produto: tipoSugerido,
        novo_unidade_medida: unidadeSugerida,
        novo_estoque_minimo: '',
      }
    })

    setItensState(novosItens)
  }, [nota, isOpen, produtosCadastrados])

  // Mutation de importação
  const importarMutation = useMutation({
    mutationFn: async (payload: ImportarNotaPayload) => {
      if (!nota) throw new Error('Nota fiscal não definida.')
      return api.post<{ ok: boolean; mensagem: string; movimentacoes_criadas: number }>(
        `/api/v1/omie/notas/${nota.id_receb}/importar/`,
        payload
      )
    },
    onSuccess: (data) => {
      toast.success(data.mensagem || 'Entradas de estoque registradas com sucesso!')
      queryClient.invalidateQueries({ queryKey: ['omie-notas'] })
      queryClient.invalidateQueries({ queryKey: ['produtos'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['movimentacoes'] })
      queryClient.invalidateQueries({ queryKey: ['produtos-opcoes'] })
      onSuccess?.()
      onClose()
    },
    onError: (err: any) => {
      toast.error(err.message || 'Erro ao importar itens da nota fiscal.')
    },
  })

  // Helpers de manipulação de itens
  const atualizarItem = (idx: number, patch: Partial<ItemFormState>) => {
    setItensState((prev) =>
      prev.map((it) => (it.idx === idx ? { ...it, ...patch } : it))
    )
  }

  const toggleSelecionarTodos = () => {
    const todosMarcados = itensState.every((it) => it.selecionado)
    setItensState((prev) => prev.map((it) => ({ ...it, selecionado: !todosMarcados })))
  }

  const itensSelecionados = itensState.filter((it) => it.selecionado)
  const totalSelecionados = itensSelecionados.length
  const totalCriar = itensSelecionados.filter((it) => it.acao === 'criar').length
  const totalVincular = itensSelecionados.filter((it) => it.acao === 'vincular').length

  // Validação para habilitar o envio
  const validacaoInvalida = useMemo(() => {
    if (totalSelecionados === 0) return 'Selecione ao menos um item para importar.'
    for (const it of itensSelecionados) {
      const qtdNum = Number(it.quantidade)
      if (isNaN(qtdNum) || qtdNum <= 0) {
        return `Quantidade inválida para o item "${it.descricao_omie}".`
      }
      if (it.acao === 'vincular' && !it.produto_id) {
        return `Selecione um produto cadastrado no SGE para "${it.descricao_omie}".`
      }
      if (it.acao === 'criar' && !it.novo_descricao.trim()) {
        return `Informe a descrição do novo produto para "${it.descricao_omie}".`
      }
    }
    return null
  }, [itensSelecionados, totalSelecionados])

  if (!nota) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validacaoInvalida) {
      toast.error(validacaoInvalida)
      return
    }

    const payload: ImportarNotaPayload = {
      numero_nfe: nota.numero_nfe,
      fornecedor_nome: nota.fornecedor_nome || nota.fornecedor_razao || '',
      fornecedor_cnpj: nota.fornecedor_cnpj || '',
      chave_nfe: nota.chave_nfe || '',
      itens: itensSelecionados.map((it) => ({
        descricao_omie: it.descricao_omie,
        codigo_omie: it.codigo_omie,
        quantidade: Number(it.quantidade),
        unidade_omie: it.unidade_omie,
        valor_unitario: it.valor_unitario,
        acao: it.acao,
        produto_id: it.acao === 'vincular' ? it.produto_id : null,
        novo_produto:
          it.acao === 'criar'
            ? {
                descricao: it.novo_descricao.trim(),
                tipo_produto: it.novo_tipo_produto,
                unidade_medida: it.novo_unidade_medida,
                estoque_minimo: it.novo_estoque_minimo ? Number(it.novo_estoque_minimo) : null,
              }
            : undefined,
        atualizar_custo: it.atualizar_custo,
      })),
    }

    importarMutation.mutate(payload)
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="4xl"
      title={
        <div className="flex items-center gap-2">
          <Package className="w-5 h-5 text-primary" />
          <span>Importar & Conciliar NF-e para o Estoque</span>
        </div>
      }
      description={
        <span>
          Mapeie os itens da nota com produtos do SGE ou cadastre novos insumos para registrar as entradas de estoque.
        </span>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Banner com Informações da NF-e */}
        <div className="p-4 rounded-xl bg-muted/40 border border-border flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-bold text-base text-foreground">
                NF-e nº {nota.numero_nfe || 'S/N'}
              </span>
              {nota.serie && (
                <Badge variant="outline" className="text-[10px]">
                  Série {nota.serie}
                </Badge>
              )}
              <Badge variant="secondary" className="text-[10px]">
                {nota.itens?.length || 0} itens na nota
              </Badge>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
              <span className="font-semibold text-foreground flex items-center gap-1">
                <Building className="w-3.5 h-3.5 text-muted-foreground" />
                {nota.fornecedor_nome || nota.fornecedor_razao || 'Fornecedor não identificado'}
              </span>
              {nota.data_emissao && (
                <span className="flex items-center gap-1">
                  • <Calendar className="w-3.5 h-3.5 text-muted-foreground" /> Emissão: {nota.data_emissao}
                </span>
              )}
            </div>
          </div>

          <div className="text-left md:text-right shrink-0">
            <span className="text-[10px] uppercase font-semibold text-muted-foreground tracking-wider block">
              Valor Faturado
            </span>
            <span className="text-xl font-extrabold text-primary">
              {formatarMoeda(nota.valor_total)}
            </span>
          </div>
        </div>

        {/* Barra de Ações Globais */}
        <div className="flex items-center justify-between gap-3 flex-wrap pt-1">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={toggleSelecionarTodos}
              className="text-xs font-semibold text-primary hover:underline"
            >
              {itensState.every((it) => it.selecionado)
                ? 'Desmarcar todos'
                : 'Selecionar todos'}
            </button>
            <span className="text-xs text-muted-foreground">
              ({totalSelecionados} de {itensState.length} selecionados)
            </span>
          </div>

          <div className="text-xs text-muted-foreground flex items-center gap-3">
            <span className="flex items-center gap-1">
              <Link2 className="w-3.5 h-3.5 text-emerald-500" />
              {totalVincular} mesclando com estoque
            </span>
            <span className="flex items-center gap-1">
              <PlusCircle className="w-3.5 h-3.5 text-primary" />
              {totalCriar} novos produtos
            </span>
          </div>
        </div>

        {/* Lista de Itens para Conciliação */}
        {carregandoOpcoes ? (
          <div className="py-12 flex flex-col items-center justify-center gap-2 text-muted-foreground">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
            <span className="text-xs">Carregando catálogo de insumos para correspondência...</span>
          </div>
        ) : (
          <div className="space-y-4 max-h-[50vh] overflow-y-auto pr-1">
            {itensState.map((item) => {
              const produtosFiltrados = produtosCadastrados.filter((p) => {
                if (!item.produto_busca) return true
                const busca = item.produto_busca.toLowerCase()
                return p.descricao.toLowerCase().includes(busca)
              })

              const produtoSelecionado = produtosCadastrados.find((p) => p.id === item.produto_id)

              return (
                <div
                  key={item.idx}
                  className={`rounded-xl border transition-all p-4 space-y-3 ${
                    item.selecionado
                      ? 'bg-card border-border shadow-xs'
                      : 'bg-muted/30 border-border/50 opacity-60'
                  }`}
                >
                  {/* Linha Superior: Checkbox, Dados da NF e Ação */}
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        checked={item.selecionado}
                        onChange={(e) =>
                          atualizarItem(item.idx, { selecionado: e.target.checked })
                        }
                        className="mt-1 h-4 w-4 rounded border-input text-primary focus:ring-primary cursor-pointer"
                        id={`check-item-${item.idx}`}
                      />
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <label
                            htmlFor={`check-item-${item.idx}`}
                            className="font-semibold text-sm text-foreground cursor-pointer"
                          >
                            {item.descricao_omie}
                          </label>
                          {item.codigo_omie && (
                            <Badge variant="outline" className="font-mono text-[10px] py-0">
                              Cód: {item.codigo_omie}
                            </Badge>
                          )}
                          {item.sugestao_automatica && item.acao === 'vincular' && (
                            <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[10px] gap-1 py-0">
                              <Sparkles className="w-3 h-3" /> Sugestão automática
                            </Badge>
                          )}
                        </div>

                        <div className="flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
                          <span>
                            Faturado: <strong className="text-foreground">{item.quantidade} {item.unidade_omie}</strong>
                          </span>
                          <span>•</span>
                          <span>
                            Preço Unit.: <strong className="text-foreground">{formatarMoeda(item.valor_unitario)}</strong>
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Botões de Ação: Vincular vs Criar */}
                    {item.selecionado && (
                      <div className="flex items-center bg-muted/60 p-0.5 rounded-lg border border-border shrink-0 self-start">
                        <button
                          type="button"
                          onClick={() => atualizarItem(item.idx, { acao: 'vincular' })}
                          className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all flex items-center gap-1 ${
                            item.acao === 'vincular'
                              ? 'bg-background text-foreground shadow-xs'
                              : 'text-muted-foreground hover:text-foreground'
                          }`}
                        >
                          <Link2 className="w-3 h-3" />
                          Mesclar c/ Estoque
                        </button>
                        <button
                          type="button"
                          onClick={() => atualizarItem(item.idx, { acao: 'criar' })}
                          className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all flex items-center gap-1 ${
                            item.acao === 'criar'
                              ? 'bg-background text-foreground shadow-xs'
                              : 'text-muted-foreground hover:text-foreground'
                          }`}
                        >
                          <PlusCircle className="w-3 h-3" />
                          Novo Insumo
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Configurações do Item Selecionado */}
                  {item.selecionado && (
                    <div className="pt-3 border-t border-border/80 grid grid-cols-1 md:grid-cols-12 gap-3 items-end">
                      {item.acao === 'vincular' ? (
                        <>
                          {/* Seletor de Produto SGE */}
                          <div className="md:col-span-6 space-y-1">
                            <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
                              Vincular ao Produto SGE <span className="text-destructive">*</span>
                            </label>
                            <div className="space-y-1.5">
                              {/* Busca rápida de produto */}
                              <div className="relative">
                                <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted-foreground pointer-events-none" />
                                <Input
                                  placeholder="Filtrar por nome do produto..."
                                  value={item.produto_busca}
                                  onChange={(e) =>
                                    atualizarItem(item.idx, { produto_busca: e.target.value })
                                  }
                                  className="h-8 pl-8 text-xs"
                                />
                              </div>

                              <select
                                value={item.produto_id ?? ''}
                                onChange={(e) =>
                                  atualizarItem(item.idx, {
                                    produto_id: e.target.value ? Number(e.target.value) : null,
                                    sugestao_automatica: false,
                                  })
                                }
                                className="w-full h-8 px-2 text-xs rounded-md border border-input bg-background"
                                required
                              >
                                <option value="">— Selecione o produto no estoque —</option>
                                {produtosFiltrados.map((p) => (
                                  <option key={p.id} value={p.id}>
                                    {p.descricao} (Saldo: {p.quantidade_formatada})
                                  </option>
                                ))}
                              </select>

                              {produtoSelecionado && (
                                <p className="text-[11px] text-muted-foreground">
                                  Saldo atual: <span className="font-semibold text-foreground">{produtoSelecionado.quantidade_formatada}</span>
                                  {produtoSelecionado.preco_custo !== null && (
                                    <> • Custo atual: <span className="font-semibold text-foreground">{formatarMoeda(produtoSelecionado.preco_custo)}</span></>
                                  )}
                                </p>
                              )}
                            </div>
                          </div>
                        </>
                      ) : (
                        <>
                          {/* Formulário de Criação de Novo Produto */}
                          <div className="md:col-span-3 space-y-1">
                            <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
                              Descrição no SGE <span className="text-destructive">*</span>
                            </label>
                            <Input
                              value={item.novo_descricao}
                              onChange={(e) =>
                                atualizarItem(item.idx, { novo_descricao: e.target.value })
                              }
                              placeholder="Nome do produto"
                              className="h-8 text-xs"
                              required
                            />
                          </div>

                          <div className="md:col-span-2 space-y-1">
                            <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
                              Tipo
                            </label>
                            <select
                              value={item.novo_tipo_produto}
                              onChange={(e) =>
                                atualizarItem(item.idx, { novo_tipo_produto: e.target.value })
                              }
                              className="w-full h-8 px-2 text-xs rounded-md border border-input bg-background"
                            >
                              {(opcoes?.tipos_produto || [
                                { value: 'TECIDO', label: 'Tecido' },
                                { value: 'PAPEL', label: 'Papel' },
                                { value: 'TINTA', label: 'Tinta' },
                                { value: 'AVIAMENTO', label: 'Aviamento' },
                                { value: 'OUTRO', label: 'Outro' },
                              ]).map((t: { value: string; label: string }) => (
                                <option key={t.value} value={t.value}>
                                  {t.label}
                                </option>
                              ))}
                            </select>
                          </div>

                          <div className="md:col-span-1 space-y-1">
                            <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
                              UN
                            </label>
                            <select
                              value={item.novo_unidade_medida}
                              onChange={(e) =>
                                atualizarItem(item.idx, { novo_unidade_medida: e.target.value })
                              }
                              className="w-full h-8 px-2 text-xs rounded-md border border-input bg-background"
                            >
                              {(opcoes?.unidades_medida || [
                                { value: 'M', label: 'Metros' },
                                { value: 'L', label: 'Litros' },
                                { value: 'UN', label: 'Unidade' },
                                { value: 'KG', label: 'Kg' },
                                { value: 'RL', label: 'Rolo' },
                              ]).map((u: { value: string; label: string }) => (
                                <option key={u.value} value={u.value}>
                                  {u.label}
                                </option>
                              ))}
                            </select>
                          </div>
                        </>
                      )}

                      {/* Quantidade a dar entrada */}
                      <div className="md:col-span-3 space-y-1">
                        <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
                          Qtd Entrada <span className="text-destructive">*</span>
                        </label>
                        <Input
                          type="number"
                          step="0.01"
                          min="0.01"
                          value={item.quantidade}
                          onChange={(e) =>
                            atualizarItem(item.idx, { quantidade: e.target.value })
                          }
                          className="h-8 text-xs font-semibold"
                          required
                        />
                      </div>

                      {/* Checkbox Atualizar Custo */}
                      <div className="md:col-span-3 flex items-center h-8 gap-2">
                        <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                          <input
                            type="checkbox"
                            checked={item.atualizar_custo}
                            onChange={(e) =>
                              atualizarItem(item.idx, { atualizar_custo: e.target.checked })
                            }
                            className="rounded border-input text-primary focus:ring-primary cursor-pointer"
                          />
                          <span>Atualizar custo ({formatarMoeda(item.valor_unitario)})</span>
                        </label>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}

        {/* Rodapé e Botões de Submissão */}
        <div className="pt-4 border-t border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="text-xs text-muted-foreground">
            {totalSelecionados > 0 ? (
              <span>
                Serão registradas <strong>{totalSelecionados}</strong> entrada(s) de estoque
                {totalCriar > 0 && <> e <strong>{totalCriar}</strong> novo(s) produto(s) cadastrado(s)</>}.
              </span>
            ) : (
              <span className="text-amber-500 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" /> Nenhum item selecionado.
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 justify-end">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={importarMutation.isPending}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={importarMutation.isPending || Boolean(validacaoInvalida)}
              className="gap-1.5"
            >
              {importarMutation.isPending ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Registrando entradas...
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Confirmar Entrada no Estoque
                </>
              )}
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  )
}
