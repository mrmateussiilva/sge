import { useState } from 'react'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { useDebounce } from '@/hooks/useDebounce'
import {
  History,
  Search,
  ChevronLeft,
  ChevronRight,
  User,
  Clock,
  Layers,
} from 'lucide-react'
import { api } from '@/api/client'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'

export function LogsPage() {
  const [pagina, setPagina] = useState(1)
  const [busca, setBusca] = useState('')
  const [acaoFiltro, setAcaoFiltro] = useState('')
  const debouncedBusca = useDebounce(busca, 350)

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['logs', pagina, debouncedBusca, acaoFiltro],
    queryFn: () => {
      const params = new URLSearchParams()
      params.set('page', String(pagina))
      params.set('page_size', '20')
      if (debouncedBusca.trim()) params.set('busca', debouncedBusca.trim())
      if (acaoFiltro) params.set('acao', acaoFiltro)
      return api.get<any>(`/api/v1/logs/?${params.toString()}`)
    },
    placeholderData: keepPreviousData,
  })

  const itens = data?.itens || []
  const paginacao = data?.paginacao || {
    pagina_atual: 1,
    total_paginas: 1,
    total_itens: 0,
    tem_proxima: false,
    tem_anterior: false,
  }
  const acoesDisponiveis = data?.acoes_disponiveis || []

  function handleBuscaChange(valor: string) {
    setBusca(valor)
    setPagina(1)
  }

  function handleAcaoChange(acao: string) {
    setAcaoFiltro(acao)
    setPagina(1)
  }

  function renderAcaoBadge(acao: string) {
    switch (acao) {
      case 'ENTRADA':
      case 'RECEBER':
        return (
          <Badge className="bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            {acao}
          </Badge>
        )
      case 'SAIDA':
        return (
          <Badge className="bg-blue-600/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
            {acao}
          </Badge>
        )
      case 'EXCLUIR':
      case 'CANCELAR':
        return (
          <Badge className="bg-destructive/10 text-destructive border border-destructive/20">
            {acao}
          </Badge>
        )
      case 'CRIAR':
        return (
          <Badge className="bg-purple-600/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
            {acao}
          </Badge>
        )
      case 'APROVAR':
        return (
          <Badge className="bg-teal-600/10 text-teal-600 dark:text-teal-400 border border-teal-500/20">
            {acao}
          </Badge>
        )
      default:
        return <Badge variant="outline">{acao}</Badge>
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Trilha de Auditoria & Segurança</h1>
        <p className="text-sm text-muted-foreground">
          Registro cronológico e imutável de todas as ações operacionais, alterações cadastrais e movimentações.
        </p>
      </div>

      {/* Filtros e Busca */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        {/* Chips de Ação */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 max-w-full">
          <Button
            variant={acaoFiltro === '' ? 'default' : 'outline'}
            size="sm"
            onClick={() => handleAcaoChange('')}
            className="h-8 text-xs shrink-0"
          >
            Todas ({paginacao.total_itens})
          </Button>
          {acoesDisponiveis.map((a: any) => {
            const isSelected = acaoFiltro === a.value
            return (
              <Button
                key={a.value}
                variant={isSelected ? 'default' : 'outline'}
                size="sm"
                onClick={() => handleAcaoChange(isSelected ? '' : a.value)}
                className="h-8 text-xs shrink-0"
              >
                {a.label}
              </Button>
            )
          })}
        </div>

        {/* Input de Busca */}
        <div className="relative w-full md:w-72 shrink-0">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            value={busca}
            onChange={(e) => handleBuscaChange(e.target.value)}
            placeholder="Buscar por descrição, usuário..."
            className="pl-9 h-9"
          />
        </div>
      </div>

      {/* Tabela de Logs */}
      <Card>
        {/* Barra de progresso sutil para re-fetches */}
        <div
          className={`h-0.5 rounded-t-xl transition-all duration-300 ${
            isFetching && !isLoading ? 'bg-primary animate-pulse' : 'bg-transparent'
          }`}
        />
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-12 text-center text-sm text-muted-foreground">
              Carregando registros de auditoria...
            </div>
          ) : itens.length === 0 ? (
            <div className="p-12 text-center space-y-2">
              <History className="w-10 h-10 text-muted-foreground/60 mx-auto" />
              <p className="font-semibold text-sm text-foreground">
                Nenhum registro encontrado
              </p>
              <p className="text-xs text-muted-foreground">
                Tente ajustar os filtros ou os termos de pesquisa acima.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs uppercase bg-muted/50 text-muted-foreground border-b border-border">
                  <tr>
                    <th className="px-4 py-3.5 font-semibold">Data / Hora</th>
                    <th className="px-4 py-3.5 font-semibold">Ação</th>
                    <th className="px-4 py-3.5 font-semibold">Usuário</th>
                    <th className="px-4 py-3.5 font-semibold">Módulo</th>
                    <th className="px-4 py-3.5 font-semibold">Descrição do Evento</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {itens.map((log: any) => (
                    <tr key={log.id} className="hover:bg-muted/40 transition-colors">
                      <td className="px-4 py-3.5 whitespace-nowrap text-xs text-muted-foreground font-mono">
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-muted-foreground" />
                          <span>{log.data_formatada}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        {renderAcaoBadge(log.acao)}
                      </td>
                      <td className="px-4 py-3.5 font-medium text-foreground whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <User className="w-3.5 h-3.5 text-muted-foreground" />
                          <span>{log.usuario}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-xs text-muted-foreground whitespace-nowrap">
                        {log.modelo ? (
                          <div className="flex items-center gap-1">
                            <Layers className="w-3 h-3 text-muted-foreground" />
                            <span>{log.modelo}</span>
                          </div>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-foreground max-w-md">
                        {log.descricao}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Barra de Paginação */}
      {paginacao.total_paginas > 1 && (
        <div className="flex items-center justify-between gap-4 pt-2">
          <div className="text-xs text-muted-foreground">
            Página <span className="font-semibold text-foreground">{paginacao.pagina_atual}</span> de{' '}
            <span className="font-semibold text-foreground">{paginacao.total_paginas}</span> ({paginacao.total_itens} registros)
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPagina((p) => Math.max(1, p - 1))}
              disabled={!paginacao.tem_anterior || isLoading}
              className="gap-1 h-8 text-xs"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Anterior</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPagina((p) => p + 1)}
              disabled={!paginacao.tem_proxima || isLoading}
              className="gap-1 h-8 text-xs"
            >
              <span>Próxima</span>
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
