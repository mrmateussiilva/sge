import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { useDebounce } from '@/hooks/useDebounce'
import {
  ArrowLeftRight,
  Plus,
  Search,
  ArrowDownRight,
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  Loader2,
} from 'lucide-react'
import { api } from '@/api/client'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { MovimentacaoModal } from '@/components/movimentacoes/MovimentacaoModal'
import type { MovimentacaoItem, Paginacao } from '@/types'

export function MovimentacoesPage() {
  const [modalOpen, setModalOpen] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()

  const tipo = searchParams.get('tipo') || ''
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
    queryKey: ['movimentacoes', { busca: debouncedBusca, tipo, page }],
    queryFn: () => {
      const params = new URLSearchParams()
      if (debouncedBusca) params.set('busca', debouncedBusca)
      if (tipo) params.set('tipo', tipo)
      params.set('page', String(page))
      params.set('page_size', '25')
      return api.get<{ ok: boolean; itens: MovimentacaoItem[]; paginacao: Paginacao }>(
        `/api/v1/movimentacoes/?${params.toString()}`
      )
    },
    placeholderData: keepPreviousData,
  })

  function handleTipoChange(novoTipo: string) {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (novoTipo) {
          next.set('tipo', novoTipo)
        } else {
          next.delete('tipo')
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
          <h1 className="text-2xl font-bold tracking-tight">Registro de Movimentações</h1>
          <p className="text-sm text-muted-foreground">
            Histórico e auditoria de todas as entradas e saídas físicas do estoque.
          </p>
        </div>
        <Button
          onClick={() => setModalOpen(true)}
          className="gap-1.5 self-start sm:self-auto shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>Registrar Movimentação</span>
        </Button>
      </div>

      {/* Barra de Filtros e Busca */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Buscar por produto, observação ou usuário..."
            value={busca}
            onChange={(e) => {
              setBusca(e.target.value)
              handlePageChange(1)
            }}
            className="w-full pl-9 pr-4 py-2 rounded-lg border border-input bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        {/* Chips de Tipo */}
        <div className="flex items-center gap-1.5">
          {[
            { key: '', label: 'Todas' },
            { key: 'ENTRADA', label: 'Entradas' },
            { key: 'SAIDA', label: 'Saídas' },
          ].map((t) => (
            <button
              key={t.key}
              onClick={() => handleTipoChange(t.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                tipo === t.key
                  ? 'bg-primary text-primary-foreground font-semibold shadow-xs'
                  : 'bg-card border border-border text-muted-foreground hover:bg-muted'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tabela de Movimentações */}
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
              <p>Carregando histórico de movimentações...</p>
            </div>
          ) : data?.itens?.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <ArrowLeftRight className="w-10 h-10 text-muted-foreground mx-auto" />
              <p className="font-semibold text-base">Nenhuma movimentação encontrada</p>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                Não há registros com os filtros atuais.
              </p>
            </div>
          ) : (
            <>
              {/* Tabela Desktop */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase bg-muted/40 text-muted-foreground border-b border-border">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Tipo</th>
                      <th className="px-4 py-3 font-semibold">Produto</th>
                      <th className="px-4 py-3 font-semibold">Quantidade</th>
                      <th className="px-4 py-3 font-semibold">Motivo</th>
                      <th className="px-4 py-3 font-semibold">Usuário</th>
                      <th className="px-4 py-3 font-semibold">Data / Hora</th>
                      <th className="px-4 py-3 font-semibold">Observação</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data?.itens?.map((mov) => {
                      const isEntrada = mov.tipo === 'ENTRADA'
                      return (
                        <tr key={mov.id} className="hover:bg-muted/30 transition-colors">
                          <td className="px-4 py-3">
                            <Badge variant={isEntrada ? 'success' : 'danger'} className="gap-1">
                              {isEntrada ? (
                                <ArrowDownRight className="w-3 h-3" />
                              ) : (
                                <ArrowUpRight className="w-3 h-3" />
                              )}
                              <span>{mov.tipo_display}</span>
                            </Badge>
                          </td>
                          <td className="px-4 py-3 font-medium text-foreground">
                            {mov.produto_descricao}
                          </td>
                          <td className="px-4 py-3 font-bold font-mono">
                            <span className={isEntrada ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}>
                              {isEntrada ? '+' : '-'}
                              {mov.quantidade_formatada}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-muted-foreground">
                            {mov.motivo_display || '—'}
                          </td>
                          <td className="px-4 py-3 text-muted-foreground">{mov.usuario}</td>
                          <td className="px-4 py-3 text-muted-foreground whitespace-nowrap text-xs">
                            {mov.data_formatada}
                          </td>
                          <td className="px-4 py-3 text-muted-foreground text-xs truncate max-w-xs">
                            {mov.observacao || '—'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              {/* Cards Mobile */}
              <div className="block md:hidden divide-y divide-border">
                {data?.itens?.map((mov) => {
                  const isEntrada = mov.tipo === 'ENTRADA'
                  return (
                    <div key={mov.id} className="p-4 space-y-2 bg-card">
                      <div className="flex items-start justify-between gap-2">
                        <Badge variant={isEntrada ? 'success' : 'danger'}>
                          {mov.tipo_display}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {mov.data_formatada}
                        </span>
                      </div>

                      <div>
                        <p className="font-semibold text-sm text-foreground">
                          {mov.produto_descricao}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Motivo: {mov.motivo_display || 'Não especificado'}
                        </p>
                      </div>

                      <div className="flex items-center justify-between pt-1 text-xs">
                        <span className="text-muted-foreground">Por: {mov.usuario}</span>
                        <span className="font-bold font-mono text-base">
                          {isEntrada ? '+' : '-'}
                          {mov.quantidade_formatada}
                        </span>
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
                    <strong>{data.paginacao.total_paginas}</strong> ({data.paginacao.total_itens} movimentações)
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

      {/* Modal de Movimentação */}
      <MovimentacaoModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={refetch}
      />
    </div>
  )
}
