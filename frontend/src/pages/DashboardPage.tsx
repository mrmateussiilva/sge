import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Boxes,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  DollarSign,
  PackageX,
  Plus,
  ArrowLeftRight,
  RefreshCw,
  Bell,
} from 'lucide-react'
import { api } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Link } from 'react-router-dom'
import { DashboardChart } from '@/components/dashboard/DashboardChart'
import { MovimentacaoModal } from '@/components/movimentacoes/MovimentacaoModal'
import { NotificacaoTesteModal } from '@/components/notificacoes/NotificacaoTesteModal'
import type { DashboardResponse } from '@/types'

export function DashboardPage() {
  const [modalMovOpen, setModalMovOpen] = useState(false)
  const [modalNotificacaoOpen, setModalNotificacaoOpen] = useState(false)
  const [produtoParaMov, setProdutoParaMov] = useState<any>(null)

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get<DashboardResponse>('/api/v1/dashboard/'),
    refetchInterval: 60_000,
  })

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="h-28 bg-muted/40" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-2 h-80 bg-muted/40" />
          <Card className="h-80 bg-muted/40" />
        </div>
      </div>
    )
  }

  const resumo = data?.resumo
  const itensCriticos = data?.itens_criticos || []
  const ultimasMovs = data?.ultimas_movimentacoes || []

  function handleRepor(item: any) {
    setProdutoParaMov(item)
    setModalMovOpen(true)
  }

  return (
    <div className="space-y-6">
      {/* Top Banner / Quick Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Painel de Estoque</h1>
          <p className="text-sm text-muted-foreground">
            Acompanhamento em tempo real de saldo físico e indicadores de movimentação.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            title="Atualizar dados agora"
            className="gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin text-primary' : ''}`} />
            <span className="hidden sm:inline">Atualizar</span>
          </Button>
          <Button
            size="sm"
            className="gap-1.5 shadow-sm"
            onClick={() => {
              setProdutoParaMov(null)
              setModalMovOpen(true)
            }}
          >
            <ArrowLeftRight className="w-4 h-4" />
            <span>Movimentar</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 border-primary/20 text-primary hover:bg-primary/10"
            onClick={() => setModalNotificacaoOpen(true)}
            title="Testar Notificação"
          >
            <Bell className="w-4 h-4" />
            <span className="hidden sm:inline">Testar Notificação</span>
          </Button>
          <Button asChild variant="outline" size="sm" className="gap-1.5">
            <Link to="/produtos">
              <Plus className="w-4 h-4" />
              <span>Ver Produtos</span>
            </Link>
          </Button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Total Itens */}
        <Card className="hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Total de Itens
            </CardTitle>
            <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
              <Boxes className="w-4 h-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{resumo?.total_itens || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">Materiais cadastrados</p>
          </CardContent>
        </Card>

        {/* Card 2: Valor do Estoque */}
        <Card className="hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Patrimônio em Estoque
            </CardTitle>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
              <DollarSign className="w-4 h-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold valor-sensivel">
              {resumo?.valor_total_formatado || 'R$ 0,00'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {resumo?.produtos_sem_custo
                ? `${resumo.produtos_sem_custo} itens sem custo`
                : 'Cálculo 100% conhecido'}
            </p>
          </CardContent>
        </Card>

        {/* Card 3: Estoque Baixo */}
        <Card className="hover:shadow-md transition-shadow border-amber-500/20">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-400">
              Estoque Baixo
            </CardTitle>
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">
              {resumo?.estoque_baixo || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Abaixo do mínimo recomendado</p>
          </CardContent>
        </Card>

        {/* Card 4: Estoque Zerado */}
        <Card className="hover:shadow-md transition-shadow border-rose-500/20">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-rose-700 dark:text-rose-400">
              Estoque Zerado
            </CardTitle>
            <div className="w-8 h-8 rounded-lg bg-rose-500/10 text-rose-600 dark:text-rose-400 flex items-center justify-center">
              <PackageX className="w-4 h-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-rose-600 dark:text-rose-400">
              {resumo?.estoque_zerado || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Itens sem saldo físico</p>
          </CardContent>
        </Card>
      </div>

      {/* Gráficos Analíticos */}
      <DashboardChart />

      {/* Main Grid: Itens Críticos & Últimas Movimentações */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Itens em Atenção */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Atenção: Itens em Nível Crítico</CardTitle>
              <CardDescription>Produtos que demandam reposição urgente</CardDescription>
            </div>
            <Badge variant="warning">{itensCriticos.length}</Badge>
          </CardHeader>
          <CardContent>
            {itensCriticos.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                Nenhum item com estoque baixo no momento. Parabéns!
              </p>
            ) : (
              <div className="divide-y divide-border">
                {itensCriticos.map((item) => (
                  <div
                    key={item.id}
                    className="py-3 flex items-center justify-between gap-3 text-sm first:pt-0 last:pb-0"
                  >
                    <div className="min-w-0">
                      <Link
                        to={`/produtos/${item.id}`}
                        className="font-semibold truncate hover:text-primary transition-colors block"
                      >
                        {item.descricao}
                      </Link>
                      <p className="text-xs text-muted-foreground truncate">
                        {item.fornecedor || 'Sem fornecedor'} • Mín: {item.estoque_minimo_formatado || item.estoque_minimo || 'Sem mínimo'}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge variant={item.status_estoque === 'ZERADO' ? 'danger' : 'warning'}>
                        {item.quantidade_formatada}
                      </Badge>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 text-xs text-primary hover:bg-primary/10"
                        onClick={() => handleRepor(item)}
                      >
                        Repor
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Últimas Movimentações */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Últimas Movimentações</CardTitle>
              <CardDescription>Entradas e saídas registradas recentemente</CardDescription>
            </div>
            <Button asChild variant="ghost" size="sm" className="h-8 text-xs">
              <Link to="/movimentacoes">Ver todas</Link>
            </Button>
          </CardHeader>
          <CardContent>
            {ultimasMovs.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                Nenhuma movimentação registrada recentemente.
              </p>
            ) : (
              <div className="divide-y divide-border">
                {ultimasMovs.map((mov) => {
                  const isEntrada = mov.tipo === 'ENTRADA'
                  return (
                    <div
                      key={mov.id}
                      className="py-3 flex items-center justify-between gap-3 text-sm first:pt-0 last:pb-0"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div
                          className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                            isEntrada
                              ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                              : 'bg-rose-500/10 text-rose-600 dark:text-rose-400'
                          }`}
                        >
                          {isEntrada ? (
                            <ArrowDownRight className="w-4 h-4" />
                          ) : (
                            <ArrowUpRight className="w-4 h-4" />
                          )}
                        </div>
                        <div className="min-w-0">
                          <p className="font-semibold truncate">{mov.produto_descricao}</p>
                          <p className="text-xs text-muted-foreground">
                            {mov.data_formatada} • Por {mov.usuario}
                          </p>
                        </div>
                      </div>
                      <Badge variant={isEntrada ? 'success' : 'danger'} className="shrink-0 font-mono">
                        {isEntrada ? '+' : '-'}
                        {mov.quantidade_formatada}
                      </Badge>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Modal de Movimentação Integrado */}
      <MovimentacaoModal
        isOpen={modalMovOpen}
        onClose={() => {
          setModalMovOpen(false)
          setProdutoParaMov(null)
        }}
        produtoPadrao={produtoParaMov}
        onSuccess={refetch}
      />

      {/* Modal de Teste de Notificação */}
      <NotificacaoTesteModal
        isOpen={modalNotificacaoOpen}
        onClose={() => setModalNotificacaoOpen(false)}
      />
    </div>
  )
}
