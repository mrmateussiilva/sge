import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  PackageCheck,
  FileSpreadsheet,
  Truck,
  Calendar,
  Loader2,
} from 'lucide-react'
import { api } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

export function OrdemDetalhePage() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['ordem-detalhe', id],
    queryFn: () => api.get<any>(`/api/v1/ordens/${id}/`),
    enabled: Boolean(id),
  })

  // Mutations para ciclo de vida da ordem
  const aprovarMutation = useMutation({
    mutationFn: () => api.post(`/api/v1/ordens/${id}/aprovar/`),
    onSuccess: () => {
      toast.success('Ordem de compra aprovada!')
      queryClient.invalidateQueries({ queryKey: ['ordens'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
      refetch()
    },
    onError: (err: any) => toast.error(err.message || 'Erro ao aprovar ordem.'),
  })

  const cancelarMutation = useMutation({
    mutationFn: () => api.post(`/api/v1/ordens/${id}/cancelar/`),
    onSuccess: () => {
      toast.success('Ordem de compra cancelada.')
      queryClient.invalidateQueries({ queryKey: ['ordens'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
      refetch()
    },
    onError: (err: any) => toast.error(err.message || 'Erro ao cancelar ordem.'),
  })

  const receberMutation = useMutation({
    mutationFn: () => api.post(`/api/v1/ordens/${id}/receber/`),
    onSuccess: () => {
      toast.success('Ordem recebida! Os itens deram entrada física no estoque.')
      queryClient.invalidateQueries({ queryKey: ['ordens'] })
      queryClient.invalidateQueries({ queryKey: ['produtos'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['movimentacoes'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
      refetch()
    },
    onError: (err: any) => toast.error(err.message || 'Erro ao receber ordem.'),
  })

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-48 bg-muted rounded" />
        <div className="h-36 bg-muted/40 rounded-xl" />
        <div className="h-64 bg-muted/40 rounded-xl" />
      </div>
    )
  }

  const ordem = data?.ordem
  const itens = data?.itens || []

  if (!ordem) {
    return (
      <div className="text-center py-16 space-y-4">
        <FileSpreadsheet className="w-12 h-12 text-muted-foreground mx-auto" />
        <h2 className="text-lg font-bold">Ordem de compra não encontrada</h2>
        <Button asChild variant="outline">
          <Link to="/ordens">Voltar para a lista</Link>
        </Button>
      </div>
    )
  }

  const isPendente = ordem.status === 'PENDENTE'
  const isAprovada = ordem.status === 'APROVADA'
  const isRecebida = ordem.status === 'RECEBIDA'

  return (
    <div className="space-y-6">
      {/* Top Bar Back Link & Ações */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <Button asChild variant="ghost" size="sm" className="gap-1.5 text-muted-foreground self-start">
          <Link to="/ordens">
            <ArrowLeft className="w-4 h-4" />
            <span>Voltar às Ordens</span>
          </Link>
        </Button>

        {/* Botões contextuais de transição de status */}
        <div className="flex items-center gap-2">
          {isPendente && (
            <>
              <Button
                variant="outline"
                size="sm"
                className="text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/20 gap-1.5"
                disabled={cancelarMutation.isPending}
                onClick={() => cancelarMutation.mutate()}
              >
                <XCircle className="w-4 h-4" />
                <span>Cancelar</span>
              </Button>

              <Button
                size="sm"
                className="gap-1.5 bg-primary shadow-sm"
                disabled={aprovarMutation.isPending}
                onClick={() => aprovarMutation.mutate()}
              >
                {aprovarMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="w-4 h-4" />
                )}
                <span>Aprovar Ordem</span>
              </Button>
            </>
          )}

          {isAprovada && (
            <>
              <Button
                variant="outline"
                size="sm"
                className="text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/20 gap-1.5"
                disabled={cancelarMutation.isPending}
                onClick={() => cancelarMutation.mutate()}
              >
                <XCircle className="w-4 h-4" />
                <span>Cancelar</span>
              </Button>

              <Button
                size="sm"
                className="gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
                disabled={receberMutation.isPending}
                onClick={() => receberMutation.mutate()}
              >
                {receberMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <PackageCheck className="w-4 h-4" />
                )}
                <span>Receber no Estoque</span>
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Hero Header */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1.5">
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold tracking-tight">
                  Ordem de Compra #{ordem.id}
                </h1>
                <Badge
                  variant={
                    isRecebida
                      ? 'success'
                      : isAprovada
                      ? 'default'
                      : isPendente
                      ? 'warning'
                      : 'destructive'
                  }
                >
                  {ordem.status_display}
                </Badge>
              </div>

              <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground pt-1">
                <span className="flex items-center gap-1">
                  <Truck className="w-3.5 h-3.5" />
                  <span>{ordem.fornecedor?.nome || 'Sem fornecedor'}</span>
                </span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5" />
                  <span>{ordem.data_criacao_formatada}</span>
                </span>
              </div>

              {ordem.observacao && (
                <p className="text-xs text-foreground bg-muted/40 p-2 rounded-md mt-2 max-w-xl">
                  <strong>Observação:</strong> {ordem.observacao}
                </p>
              )}
            </div>

            {/* Total da Ordem */}
            <div className="text-right sm:border-l sm:border-border sm:pl-6">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground block">
                Valor Total do Pedido
              </span>
              <span className="text-2xl sm:text-3xl font-extrabold text-primary valor-sensivel">
                {ordem.valor_total_formatado}
              </span>
              <span className="text-xs text-muted-foreground block mt-0.5">
                {ordem.total_itens} item(ns) incluído(s)
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabela de Itens da Ordem */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Itens Vinculados à Ordem</CardTitle>
          <CardDescription>
            Relação de insumos e matérias-primas solicitadas
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs uppercase bg-muted/40 text-muted-foreground border-b border-border">
                <tr>
                  <th className="px-4 py-3 font-semibold">Produto / Insumo</th>
                  <th className="px-4 py-3 font-semibold">Quantidade</th>
                  <th className="px-4 py-3 font-semibold">Preço Unitário</th>
                  <th className="px-4 py-3 font-semibold text-right">Subtotal</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {itens.map((item: any) => (
                  <tr key={item.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-3 font-medium text-foreground">
                      <Link
                        to={`/produtos/${item.produto_id}`}
                        className="hover:text-primary transition-colors"
                      >
                        {item.produto_descricao}
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-semibold font-mono">
                      {item.quantidade} {item.produto_unidade}
                    </td>
                    <td className="px-4 py-3 valor-sensivel text-muted-foreground font-mono">
                      {item.preco_unitario_formatado}
                    </td>
                    <td className="px-4 py-3 valor-sensivel text-right font-bold text-foreground font-mono">
                      {item.subtotal_formatado}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
