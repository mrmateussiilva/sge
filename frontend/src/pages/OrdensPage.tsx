import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { useDebounce } from '@/hooks/useDebounce'
import {
  FileSpreadsheet,
  Plus,
  Search,
  Eye,
  ChevronLeft,
  ChevronRight,
  Truck,
  Loader2,
} from 'lucide-react'
import { api } from '@/api/client'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { OrdemFormModal } from '@/components/ordens/OrdemFormModal'
import type { OrdemCompraItem, Paginacao } from '@/types'

export function OrdensPage() {
  const [modalOpen, setModalOpen] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()

  const status = searchParams.get('status') || ''
  const page = Number(searchParams.get('page')) || 1

  const [busca, setBusca] = useState(searchParams.get('busca') || '')
  const debouncedBusca = useDebounce(busca, 350)

  // Sincroniza busca na URL
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

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['ordens', { busca: debouncedBusca, status, page }],
    queryFn: () => {
      const params = new URLSearchParams()
      if (debouncedBusca) params.set('busca', debouncedBusca)
      if (status) params.set('status', status)
      params.set('page', String(page))
      params.set('page_size', '25')
      return api.get<{ ok: boolean; itens: OrdemCompraItem[]; paginacao: Paginacao }>(
        `/api/v1/ordens/?${params.toString()}`
      )
    },
    placeholderData: keepPreviousData,
  })

  function handleStatusChange(novoStatus: string) {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (novoStatus) {
          next.set('status', novoStatus)
        } else {
          next.delete('status')
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Ordens de Compra</h1>
          <p className="text-sm text-muted-foreground">
            Acompanhe pedidos a fornecedores, aprovações e recebimentos com entrada em estoque.
          </p>
        </div>
        <Button
          onClick={() => setModalOpen(true)}
          className="gap-1.5 self-start sm:self-auto shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>Nova Ordem</span>
        </Button>
      </div>

      {/* Barra de Filtros e Busca */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Buscar por fornecedor ou observação..."
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
            { key: '', label: 'Todas' },
            { key: 'PENDENTE', label: 'Pendentes' },
            { key: 'APROVADA', label: 'Aprovadas' },
            { key: 'RECEBIDA', label: 'Recebidas' },
            { key: 'CANCELADA', label: 'Canceladas' },
          ].map((st) => (
            <button
              key={st.key}
              onClick={() => handleStatusChange(st.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                status === st.key
                  ? 'bg-primary text-primary-foreground font-semibold shadow-xs'
                  : 'bg-card border border-border text-muted-foreground hover:bg-muted'
              }`}
            >
              {st.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tabela de Ordens */}
      <Card>
        {/* Barra de progresso sutil para re-fetches */}
        <div
          className={`h-0.5 rounded-t-xl transition-all duration-300 ${
            isFetching && !isLoading ? 'bg-primary animate-pulse' : 'bg-transparent'
          }`}
        />
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-12 text-center text-sm text-muted-foreground space-y-2">
              <Loader2 className="w-6 h-6 animate-spin text-primary mx-auto" />
              <p>Carregando ordens de compra...</p>
            </div>
          ) : data?.itens?.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <FileSpreadsheet className="w-10 h-10 text-muted-foreground mx-auto" />
              <p className="font-semibold text-base">Nenhuma ordem de compra encontrada</p>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                Não há pedidos registrados com os filtros atuais.
              </p>
            </div>
          ) : (
            <>
              {/* Tabela Desktop */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase bg-muted/40 text-muted-foreground border-b border-border">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Nº Ordem</th>
                      <th className="px-4 py-3 font-semibold">Fornecedor</th>
                      <th className="px-4 py-3 font-semibold">Itens</th>
                      <th className="px-4 py-3 font-semibold">Valor Total</th>
                      <th className="px-4 py-3 font-semibold">Data Criação</th>
                      <th className="px-4 py-3 font-semibold">Status</th>
                      <th className="px-4 py-3 font-semibold text-right">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data?.itens?.map((ordem) => (
                      <tr key={ordem.id} className="hover:bg-muted/30 transition-colors group">
                        <td className="px-4 py-3 font-bold text-foreground">
                          <Link
                            to={`/ordens/${ordem.id}`}
                            className="hover:text-primary transition-colors"
                          >
                            #{ordem.id}
                          </Link>
                        </td>
                        <td className="px-4 py-3 font-medium text-foreground">
                          {ordem.fornecedor?.nome || 'Sem fornecedor'}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground text-xs">
                          {ordem.total_itens} item(ns)
                        </td>
                        <td className="px-4 py-3 font-bold valor-sensivel text-foreground font-mono">
                          {ordem.valor_total_formatado}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground whitespace-nowrap text-xs">
                          {ordem.data_criacao_formatada}
                        </td>
                        <td className="px-4 py-3">
                          <Badge
                            variant={
                              ordem.status === 'RECEBIDA'
                                ? 'success'
                                : ordem.status === 'APROVADA'
                                ? 'default'
                                : ordem.status === 'PENDENTE'
                                ? 'warning'
                                : 'destructive'
                            }
                          >
                            {ordem.status_display}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Button asChild variant="ghost" size="sm" className="h-8 gap-1 text-xs">
                            <Link to={`/ordens/${ordem.id}`}>
                              <Eye className="w-3.5 h-3.5" />
                              <span>Detalhes</span>
                            </Link>
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Cards Mobile */}
              <div className="block md:hidden divide-y divide-border">
                {data?.itens?.map((ordem) => (
                  <div key={ordem.id} className="p-4 space-y-3 bg-card">
                    <div className="flex items-start justify-between">
                      <div>
                        <Link
                          to={`/ordens/${ordem.id}`}
                          className="font-bold text-base hover:text-primary transition-colors block"
                        >
                          Ordem #{ordem.id}
                        </Link>
                        <p className="text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
                          <Truck className="w-3 h-3" />
                          <span>{ordem.fornecedor?.nome || 'Sem fornecedor'}</span>
                        </p>
                      </div>

                      <Badge
                        variant={
                          ordem.status === 'RECEBIDA'
                            ? 'success'
                            : ordem.status === 'APROVADA'
                            ? 'default'
                            : ordem.status === 'PENDENTE'
                            ? 'warning'
                            : 'destructive'
                        }
                      >
                        {ordem.status_display}
                      </Badge>
                    </div>

                    <div className="flex items-center justify-between p-2.5 rounded-lg bg-muted/40 text-xs">
                      <div>
                        <span className="text-[10px] uppercase font-bold text-muted-foreground block">
                          Total ({ordem.total_itens} itens)
                        </span>
                        <span className="font-extrabold text-base valor-sensivel text-foreground font-mono">
                          {ordem.valor_total_formatado}
                        </span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {ordem.data_criacao_formatada}
                      </span>
                    </div>

                    <div className="flex justify-end pt-1">
                      <Button asChild size="sm" variant="outline" className="h-8 text-xs gap-1">
                        <Link to={`/ordens/${ordem.id}`}>
                          <Eye className="w-3.5 h-3.5" />
                          <span>Ver Ordem Completa</span>
                        </Link>
                      </Button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Paginação */}
              {data?.paginacao && data.paginacao.total_paginas > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-border bg-muted/20 text-xs text-muted-foreground">
                  <div>
                    Página <strong>{data.paginacao.pagina_atual}</strong> de{' '}
                    <strong>{data.paginacao.total_paginas}</strong> ({data.paginacao.total_itens} ordens)
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

      {/* Modal de Criação de Ordem */}
      <OrdemFormModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={refetch}
      />
    </div>
  )
}
