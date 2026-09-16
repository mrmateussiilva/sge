import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { useDebounce } from '@/hooks/useDebounce'
import { toast } from 'sonner'
import {
  Search,
  Plus,
  Boxes,
  Eye,
  ArrowLeftRight,
  Edit,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Truck,
  Loader2,
} from 'lucide-react'
import { api } from '@/api/client'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Modal } from '@/components/ui/modal'
import { MovimentacaoModal } from '@/components/movimentacoes/MovimentacaoModal'
import { ProdutoFormModal } from '@/components/produtos/ProdutoFormModal'
import type { ProdutosResponse, ProdutoItem } from '@/types'

export function ProdutosPage() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()

  const aba = searchParams.get('aba') || 'PAPEL'
  const filtroEstoque = searchParams.get('filtro') || ''
  const page = Number(searchParams.get('page')) || 1

  const [busca, setBusca] = useState(searchParams.get('busca') || '')
  const debouncedBusca = useDebounce(busca, 350)

  // Estado para highlight de item recém alterado/movimentado
  const [recemAlteradoId, setRecemAlteradoId] = useState<number | null>(null)

  // Estados de Modais
  const [modalFormOpen, setModalFormOpen] = useState(false)
  const [produtoEditando, setProdutoEditando] = useState<ProdutoItem | null>(null)

  const [modalMovOpen, setModalMovOpen] = useState(false)
  const [produtoMovimentando, setProdutoMovimentando] = useState<ProdutoItem | null>(null)

  const [produtoExcluindo, setProdutoExcluindo] = useState<ProdutoItem | null>(null)
  const [confirmacaoExcluirTexto, setConfirmacaoExcluirTexto] = useState('')

  // Sincroniza debouncedBusca na URL sem poluir o histórico
  useEffect(() => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (debouncedBusca) {
          next.set('busca', debouncedBusca)
        } else {
          next.delete('busca')
        }
        return next
      },
      { replace: true }
    )
  }, [debouncedBusca, setSearchParams])

  // Query de produtos
  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['produtos', { aba, busca: debouncedBusca, filtroEstoque, page }],
    queryFn: () => {
      const params = new URLSearchParams()
      if (aba) params.set('aba', aba)
      if (debouncedBusca) params.set('busca', debouncedBusca)
      if (filtroEstoque) params.set('filtro', filtroEstoque)
      params.set('page', String(page))
      params.set('page_size', '25')
      return api.get<ProdutosResponse>(`/api/v1/produtos/?${params.toString()}`)
    },
    placeholderData: keepPreviousData,
  })

  // Mutation de exclusão
  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.post(`/api/v1/produtos/${id}/excluir/`),
    onSuccess: () => {
      toast.success('Produto excluído com sucesso!')
      queryClient.invalidateQueries({ queryKey: ['produtos'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setProdutoExcluindo(null)
    },
    onError: (err: any) => {
      toast.error(err.message || 'Erro ao excluir produto.')
    },
  })

  function handleOpenNovo() {
    setProdutoEditando(null)
    setModalFormOpen(true)
  }

  function handleOpenEditar(p: ProdutoItem) {
    setProdutoEditando(p)
    setModalFormOpen(true)
  }

  function handleOpenMovimentar(p: ProdutoItem) {
    setProdutoMovimentando(p)
    setModalMovOpen(true)
  }

  function handleAbaChange(novaAba: string) {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        next.set('aba', novaAba)
        next.set('page', '1')
        return next
      },
      { replace: true }
    )
  }

  function handleFiltroEstoqueChange(novoFiltro: string) {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (novoFiltro) {
          next.set('filtro', novoFiltro)
        } else {
          next.delete('filtro')
        }
        next.set('page', '1')
        return next
      },
      { replace: true }
    )
  }

  function handlePageChange(novaPagina: number) {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        next.set('page', String(novaPagina))
        return next
      },
      { replace: true }
    )
  }

  function triggerItemHighlight(id: number) {
    setRecemAlteradoId(id)
    setTimeout(() => setRecemAlteradoId(null), 3000)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Catálogo de Produtos</h1>
          <p className="text-sm text-muted-foreground">
            Gerencie saldos em unidade base, preços e reposição de estoque.
          </p>
        </div>
        <Button onClick={handleOpenNovo} className="gap-1.5 self-start sm:self-auto shadow-sm">
          <Plus className="w-4 h-4" />
          <span>Novo Insumo</span>
        </Button>
      </div>

      {/* Tabs por tipo */}
      <div className="flex items-center gap-1 overflow-x-auto pb-1 border-b border-border">
        {data?.abas?.map((tab) => (
          <button
            key={tab.key}
            onClick={() => handleAbaChange(tab.key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-all whitespace-nowrap ${
              aba === tab.key
                ? 'border-primary text-primary font-semibold'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            <span>{tab.label}</span>
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                aba === tab.key
                  ? 'bg-primary/10 text-primary font-bold'
                  : 'bg-muted text-muted-foreground'
              }`}
            >
              {tab.count}
            </span>
            {tab.critical && (
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" title="Itens com estoque crítico" />
            )}
          </button>
        ))}
      </div>

      {/* Search and Filters Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Buscar por descrição ou fornecedor..."
            value={busca}
            onChange={(e) => {
              setBusca(e.target.value)
              handlePageChange(1)
            }}
            className="w-full pl-9 pr-4 py-2 rounded-lg border border-input bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        {/* Chips de Status */}
        <div className="flex items-center gap-1.5 overflow-x-auto">
          {[
            { key: '', label: 'Todos' },
            { key: 'OK', label: 'Normal' },
            { key: 'BAIXO', label: 'Estoque Baixo' },
            { key: 'ZERADO', label: 'Zerados' },
          ].map((status) => (
            <button
              key={status.key}
              onClick={() => handleFiltroEstoqueChange(status.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                filtroEstoque === status.key
                  ? 'bg-primary text-primary-foreground font-semibold shadow-xs'
                  : 'bg-card border border-border text-muted-foreground hover:bg-muted'
              }`}
            >
              {status.label}
            </button>
          ))}
        </div>
      </div>

      {/* Resumo da Listagem */}
      {data?.resumo && (
        <div className="flex flex-wrap items-center justify-between gap-4 px-4 py-2.5 bg-muted/30 rounded-lg border border-border text-xs text-muted-foreground">
          <div className="flex items-center gap-4">
            <span>
              Total nesta aba: <strong>{data.resumo.total_itens}</strong> item(ns)
            </span>
            <span className="hidden sm:inline">•</span>
            <span className="hidden sm:inline">
              Valor imobilizado: <strong className="valor-sensivel text-foreground">{data.resumo.valor_custo_formatado}</strong>
            </span>
          </div>

          <div className="flex items-center gap-3">
            {data.resumo.baixos > 0 && (
              <span className="text-amber-600 dark:text-amber-400 font-semibold">
                {data.resumo.baixos} baixo(s)
              </span>
            )}
            {data.resumo.zerados > 0 && (
              <span className="text-rose-600 dark:text-rose-400 font-semibold">
                {data.resumo.zerados} zerado(s)
              </span>
            )}
          </div>
        </div>
      )}

      {/* Lista / Tabela */}
      <Card>
        {/* Barra de progresso sutil para re-fetches (troca de aba, filtro, paginação) */}
        <div
          className={`h-0.5 rounded-t-xl transition-all duration-300 ${
            isFetching && !isLoading ? 'bg-primary animate-pulse' : 'bg-transparent'
          }`}
        />
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-12 text-center text-sm text-muted-foreground space-y-2">
              <Loader2 className="w-6 h-6 animate-spin text-primary mx-auto" />
              <p>Carregando catálogo de produtos...</p>
            </div>
          ) : data?.itens?.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <Boxes className="w-10 h-10 text-muted-foreground mx-auto" />
              <p className="font-semibold text-base">Nenhum produto encontrado</p>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                Não encontramos produtos correspondentes aos filtros aplicados nesta aba.
              </p>
              <Button size="sm" variant="outline" onClick={() => { setBusca(''); handleFiltroEstoqueChange(''); }}>
                Limpar filtros
              </Button>
            </div>
          ) : (
            <>
              {/* Tabela Desktop (md:table) */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase bg-muted/40 text-muted-foreground border-b border-border">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Descrição</th>
                      <th className="px-4 py-3 font-semibold">Fornecedor</th>
                      <th className="px-4 py-3 font-semibold">Saldo Atual</th>
                      <th className="px-4 py-3 font-semibold">Preço Custo</th>
                      <th className="px-4 py-3 font-semibold">Preço Venda</th>
                      <th className="px-4 py-3 font-semibold">Status</th>
                      <th className="px-4 py-3 font-semibold text-right">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data?.itens?.map((p) => (
                      <tr
                        key={p.id}
                        className={`transition-colors group ${
                          recemAlteradoId === p.id
                            ? 'bg-emerald-500/10 ring-1 ring-emerald-500/40'
                            : 'hover:bg-muted/30'
                        }`}
                      >
                        <td className="px-4 py-3">
                          <Link
                            to={`/produtos/${p.id}`}
                            className="font-semibold text-foreground hover:text-primary transition-colors block"
                          >
                            {p.descricao}
                          </Link>
                          {p.embalagens_estimadas > 0 && (
                            <span className="text-xs text-muted-foreground block mt-0.5">
                              ≈ {p.embalagens_estimadas}{' '}
                              {p.tipo_produto === 'TINTA' ? 'garrafas' : 'rolos est.'}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground text-xs">
                          {p.fornecedor || '—'}
                        </td>
                        <td className="px-4 py-3 font-bold text-foreground">
                          {p.quantidade_formatada}
                        </td>
                        <td className="px-4 py-3 valor-sensivel text-muted-foreground text-xs">
                          {p.preco_custo_formatado}
                        </td>
                        <td className="px-4 py-3 valor-sensivel text-muted-foreground text-xs">
                          {p.preco_venda_formatado}
                        </td>
                        <td className="px-4 py-3">
                          <Badge
                            variant={
                              p.status_estoque === 'ZERADO'
                                ? 'danger'
                                : p.status_estoque === 'BAIXO'
                                ? 'warning'
                                : 'success'
                            }
                          >
                            {p.status_estoque === 'ZERADO'
                              ? 'Zerado'
                              : p.status_estoque === 'BAIXO'
                              ? 'Baixo'
                              : 'Normal'}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-8 gap-1.5 text-xs text-primary border-primary/20 hover:bg-primary/10"
                              onClick={() => handleOpenMovimentar(p)}
                              title="Movimentar estoque deste produto"
                            >
                              <ArrowLeftRight className="w-3.5 h-3.5" />
                              <span>Movimentar</span>
                            </Button>

                            <Button
                              asChild
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-muted-foreground hover:text-foreground"
                              title="Ver detalhes"
                            >
                              <Link to={`/produtos/${p.id}`}>
                                <Eye className="w-3.5 h-3.5" />
                              </Link>
                            </Button>

                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-muted-foreground hover:text-foreground"
                              onClick={() => handleOpenEditar(p)}
                              title="Editar informações"
                            >
                              <Edit className="w-3.5 h-3.5" />
                            </Button>

                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                              onClick={() => setProdutoExcluindo(p)}
                              title="Excluir produto"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Cards Mobile (< md) */}
              <div className="block md:hidden divide-y divide-border">
                {data?.itens?.map((p) => {
                  const borderStatusColor =
                    p.status_estoque === 'ZERADO'
                      ? 'border-l-rose-500'
                      : p.status_estoque === 'BAIXO'
                      ? 'border-l-amber-500'
                      : 'border-l-emerald-500'

                  return (
                    <div
                      key={p.id}
                      className={`p-4 space-y-3 bg-card border-l-4 ${borderStatusColor}`}
                    >
                      <div>
                        <Link
                          to={`/produtos/${p.id}`}
                          className="font-bold text-base text-foreground hover:text-primary transition-colors leading-snug block"
                        >
                          {p.descricao}
                        </Link>
                        <p className="text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
                          <Truck className="w-3 h-3" />
                          <span>{p.fornecedor || 'Sem fornecedor'}</span>
                          {p.embalagens_estimadas > 0 && (
                            <span>
                              • {p.embalagens_estimadas}{' '}
                              {p.tipo_produto === 'TINTA' ? 'vidros' : 'rolos'}
                            </span>
                          )}
                        </p>
                      </div>

                      <div className="grid grid-cols-2 gap-2 p-2.5 rounded-lg bg-muted/40 text-xs">
                        <div>
                          <span className="text-[10px] uppercase font-bold text-muted-foreground block">
                            Saldo Físico
                          </span>
                          <span className="font-extrabold text-base text-foreground">
                            {p.quantidade_formatada}
                          </span>
                        </div>

                        <div>
                          <span className="text-[10px] uppercase font-bold text-muted-foreground block">
                            Custo / Venda
                          </span>
                          <span className="valor-sensivel font-semibold block text-muted-foreground">
                            {p.preco_custo_formatado}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center justify-between pt-1">
                        <Badge
                          variant={
                            p.status_estoque === 'ZERADO'
                              ? 'danger'
                              : p.status_estoque === 'BAIXO'
                              ? 'warning'
                              : 'success'
                          }
                        >
                          {p.status_estoque === 'ZERADO'
                            ? 'Zerado'
                            : p.status_estoque === 'BAIXO'
                            ? 'Estoque Baixo'
                            : 'Normal'}
                        </Badge>

                        <div className="flex items-center gap-1">
                          <Button
                            size="sm"
                            className="h-8 gap-1 text-xs"
                            onClick={() => handleOpenMovimentar(p)}
                          >
                            <ArrowLeftRight className="w-3.5 h-3.5" />
                            <span>Movimentar</span>
                          </Button>
                          <Button asChild variant="outline" size="sm" className="h-8 text-xs">
                            <Link to={`/produtos/${p.id}`}>Detalhes</Link>
                          </Button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Paginação */}
              {data?.paginacao && data.paginacao.total_paginas > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-border bg-muted/20 text-xs text-muted-foreground">
                  <div>
                    Página <strong>{data.paginacao.pagina_atual}</strong> de{' '}
                    <strong>{data.paginacao.total_paginas}</strong> ({data.paginacao.total_itens} itens)
                  </div>

                  <div className="flex items-center gap-1">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!data.paginacao.tem_anterior}
                      onClick={() => handlePageChange(Math.max(page - 1, 1))}
                      className="h-8 gap-1 text-xs"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" />
                      <span>Anterior</span>
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!data.paginacao.tem_proxima}
                      onClick={() => handlePageChange(page + 1)}
                      className="h-8 gap-1 text-xs"
                    >
                      <span>Próxima</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Modal de Movimentação Rápida */}
      <MovimentacaoModal
        isOpen={modalMovOpen}
        onClose={() => {
          setModalMovOpen(false)
          setProdutoMovimentando(null)
        }}
        produtoPadrao={produtoMovimentando}
        onSuccess={() => {
          if (produtoMovimentando) triggerItemHighlight(produtoMovimentando.id)
          refetch()
        }}
      />

      {/* Modal de Cadastro / Edição */}
      <ProdutoFormModal
        isOpen={modalFormOpen}
        onClose={() => {
          setModalFormOpen(false)
          setProdutoEditando(null)
        }}
        produtoParaEditar={produtoEditando}
        onSuccess={() => {
          if (produtoEditando?.id) triggerItemHighlight(produtoEditando.id)
          refetch()
        }}
      />

      {/* Modal de Confirmação de Exclusão Segura */}
      <Modal
        isOpen={Boolean(produtoExcluindo)}
        onClose={() => {
          setProdutoExcluindo(null)
          setConfirmacaoExcluirTexto('')
        }}
        title="Confirmar Exclusão de Produto"
        description="Esta ação removerá o cadastro do produto do sistema."
        maxWidth="sm"
      >
        <div className="space-y-4">
          <p className="text-sm text-foreground">
            Tem certeza de que deseja excluir o produto{' '}
            <strong className="text-destructive">{produtoExcluindo?.descricao}</strong>?
          </p>
          <p className="text-xs text-muted-foreground">
            Produtos que possuem movimentações ou ordens vinculadas não podem ser excluídos pelo sistema para preservar a integridade contábil.
          </p>

          <div className="space-y-1.5 pt-1">
            <label className="text-xs font-semibold text-foreground">
              Para confirmar, digite <span className="font-mono text-destructive font-bold">EXCLUIR</span> abaixo:
            </label>
            <input
              type="text"
              placeholder="Digite EXCLUIR"
              value={confirmacaoExcluirTexto}
              onChange={(e) => setConfirmacaoExcluirTexto(e.target.value)}
              className="w-full px-3 py-1.5 rounded-md border border-input bg-card text-sm focus:outline-none focus:ring-2 focus:ring-destructive/30"
              autoFocus
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setProdutoExcluindo(null)
                setConfirmacaoExcluirTexto('')
              }}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              size="sm"
              disabled={deleteMutation.isPending || confirmacaoExcluirTexto.trim().toUpperCase() !== 'EXCLUIR'}
              onClick={() => {
                if (produtoExcluindo) {
                  deleteMutation.mutate(produtoExcluindo.id)
                }
              }}
              className="gap-1.5"
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Excluindo...</span>
                </>
              ) : (
                <span>Confirmar Exclusão</span>
              )}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
