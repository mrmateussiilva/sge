import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  ArrowLeft,
  Lock,
  Download,
  Trash2,
  Search,
  CheckCircle2,
  AlertTriangle,
  User,
  Calendar,
  Layers,
  CircleDollarSign,
  TrendingUp,
} from 'lucide-react'
import { api } from '@/api/client'
import { useAuth } from '@/hooks/useAuth'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Modal } from '@/components/ui/modal'

export function FechamentoDetalhePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user } = useAuth()

  const [busca, setBusca] = useState('')
  const [modalExcluirAberto, setModalExcluirAberto] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['fechamento', id],
    queryFn: () => api.get<any>(`/api/v1/fechamentos/${id}/`),
    enabled: Boolean(id),
  })

  const excluirMutation = useMutation({
    mutationFn: async () => {
      return api.post<{ ok: boolean; mensagem?: string; erro?: string }>(
        `/api/v1/fechamentos/${id}/excluir/`,
        {}
      )
    },
    onSuccess: (res) => {
      if (res.ok) {
        toast.success(res.mensagem || 'Fechamento excluído com sucesso!')
        queryClient.invalidateQueries({ queryKey: ['fechamentos'] })
        navigate('/fechamentos')
      } else {
        toast.error(res.erro || 'Erro ao excluir fechamento.')
      }
    },
    onError: (err: any) => {
      const msg = err.response?.data?.erro || err.message || 'Erro inesperado ao excluir.'
      toast.error(msg)
    },
  })

  if (isLoading) {
    return (
      <div className="p-12 text-center text-sm text-muted-foreground animate-pulse">
        Carregando dados do fechamento histórico...
      </div>
    )
  }

  const fechamento = data?.fechamento
  const itens = data?.itens || []

  if (!fechamento) {
    return (
      <div className="p-8 text-center space-y-4">
        <p className="text-muted-foreground">Fechamento não encontrado.</p>
        <Button asChild variant="outline">
          <Link to="/fechamentos">Voltar para a lista</Link>
        </Button>
      </div>
    )
  }

  const itensFiltrados = itens.filter((item: any) => {
    if (!busca.trim()) return true
    const termo = busca.toLowerCase()
    return (
      item.descricao.toLowerCase().includes(termo) ||
      (item.categoria && item.categoria.toLowerCase().includes(termo)) ||
      (item.fornecedor && item.fornecedor.toLowerCase().includes(termo)) ||
      (item.tipo && item.tipo.toLowerCase().includes(termo))
    )
  })

  const lucroProjetado = fechamento.valor_total_venda - fechamento.valor_total
  const margemProjetada =
    fechamento.valor_total > 0
      ? ((lucroProjetado / fechamento.valor_total) * 100).toFixed(1)
      : null

  return (
    <div className="space-y-6">
      {/* Topo / Navegação */}
      <div className="flex items-center justify-between gap-4">
        <Button asChild variant="ghost" size="sm" className="gap-1 text-muted-foreground hover:text-foreground">
          <Link to="/fechamentos">
            <ArrowLeft className="w-4 h-4" />
            <span>Voltar para Fechamentos</span>
          </Link>
        </Button>

        <div className="flex items-center gap-2">
          <Button asChild variant="outline" size="sm" className="gap-1.5 shadow-2xs">
            <a href={`/api/v1/fechamentos/${fechamento.id}/exportar/`} download>
              <Download className="w-4 h-4" />
              <span>Exportar Excel (XLSX)</span>
            </a>
          </Button>

          {user?.is_superuser && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setModalExcluirAberto(true)}
              className="text-destructive hover:text-destructive hover:bg-destructive/10"
              title="Excluir este fechamento e liberar o período"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Hero Header */}
      <Card className="border-border bg-gradient-to-r from-card via-card to-primary/5">
        <CardContent className="p-6">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="p-2 rounded-lg bg-primary/10 text-primary">
                  <Lock className="w-5 h-5" />
                </span>
                <div>
                  <h1 className="text-2xl font-bold tracking-tight text-foreground">
                    Fechamento de {fechamento.periodo_formatado}
                  </h1>
                  <p className="text-xs text-muted-foreground flex items-center gap-3 pt-0.5">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-muted-foreground" />
                      Gravado em {fechamento.data_fechamento_formatada}
                    </span>
                    <span className="flex items-center gap-1">
                      <User className="w-3.5 h-3.5 text-muted-foreground" />
                      Responsável: <strong className="text-foreground">{fechamento.usuario}</strong>
                    </span>
                  </p>
                </div>
              </div>
              {fechamento.observacao && (
                <p className="text-xs text-muted-foreground/90 italic pt-1 pl-1">
                  "{fechamento.observacao}"
                </p>
              )}
            </div>

            <div className="flex items-center gap-2 self-start lg:self-auto">
              {fechamento.calculo_completo ? (
                <Badge className="bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-medium text-xs py-1">
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Valuation 100% Precificado
                </Badge>
              ) : (
                <Badge className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 font-medium text-xs py-1">
                  <AlertTriangle className="w-3.5 h-3.5 mr-1" /> {fechamento.produtos_sem_custo} item(ns) sem custo
                </Badge>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total de Itens */}
        <Card>
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <span className="text-xs text-muted-foreground font-medium">Itens no Snapshot</span>
              <div className="text-2xl font-bold tracking-tight mt-0.5">
                {fechamento.total_itens}
              </div>
            </div>
            <div className="p-2.5 rounded-lg bg-blue-500/10 text-blue-500">
              <Layers className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        {/* Valuation Custo */}
        <Card>
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <span className="text-xs text-muted-foreground font-medium">Valuation (Preço de Custo)</span>
              <div className="text-2xl font-bold tracking-tight mt-0.5 valor-sensivel text-foreground">
                {fechamento.valor_total_formatado}
              </div>
            </div>
            <div className="p-2.5 rounded-lg bg-primary/10 text-primary">
              <CircleDollarSign className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        {/* Valuation Venda */}
        <Card>
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <span className="text-xs text-muted-foreground font-medium">Potencial de Venda</span>
              <div className="text-2xl font-bold tracking-tight mt-0.5 valor-sensivel text-foreground">
                {fechamento.valor_total_venda_formatado}
              </div>
            </div>
            <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-500">
              <TrendingUp className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        {/* Margem Projetada */}
        <Card>
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <span className="text-xs text-muted-foreground font-medium">Margem Projetada</span>
              <div className="text-2xl font-bold tracking-tight mt-0.5 text-foreground">
                {margemProjetada ? `+${margemProjetada}%` : '—'}
              </div>
            </div>
            <div className="p-2.5 rounded-lg bg-purple-500/10 text-purple-500">
              <TrendingUp className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabela de Itens Congelados */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="relative w-full sm:max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Filtrar por item, categoria..."
              className="pl-9"
            />
          </div>
          <span className="text-xs text-muted-foreground self-end sm:self-auto">
            Exibindo <span className="font-semibold text-foreground">{itensFiltrados.length}</span> de {itens.length} insumos congelados
          </span>
        </div>

        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs uppercase bg-muted/50 text-muted-foreground border-b border-border">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Descrição do Insumo</th>
                    <th className="px-4 py-3 font-semibold">Tipo</th>
                    <th className="px-4 py-3 font-semibold">Categoria</th>
                    <th className="px-4 py-3 font-semibold text-right">Saldo Físico</th>
                    <th className="px-4 py-3 font-semibold text-right">Custo Unit.</th>
                    <th className="px-4 py-3 font-semibold text-right">Subtotal Custo</th>
                    <th className="px-4 py-3 font-semibold text-right">Preço Venda</th>
                    <th className="px-4 py-3 font-semibold text-right">Subtotal Venda</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {itensFiltrados.map((it: any) => (
                    <tr key={it.id} className="hover:bg-muted/40 transition-colors">
                      <td className="px-4 py-3 font-medium text-foreground">
                        {it.descricao}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {it.tipo}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {it.categoria}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-foreground">
                        {it.quantidade.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 2 })} {it.unidade}
                      </td>
                      <td className="px-4 py-3 text-right valor-sensivel text-xs text-muted-foreground">
                        {it.preco_custo_formatado}
                      </td>
                      <td className="px-4 py-3 text-right valor-sensivel font-semibold text-foreground">
                        {it.valor_custo_formatado}
                      </td>
                      <td className="px-4 py-3 text-right valor-sensivel text-xs text-muted-foreground">
                        {it.preco_venda_formatado}
                      </td>
                      <td className="px-4 py-3 text-right valor-sensivel font-semibold text-foreground">
                        {it.valor_venda_formatado}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Modal Confirmação de Exclusão */}
      <Modal
        isOpen={modalExcluirAberto}
        onClose={() => setModalExcluirAberto(false)}
        title={
          <div className="flex items-center gap-2 text-destructive">
            <Trash2 className="w-5 h-5" />
            <span>Excluir Fechamento Histórico</span>
          </div>
        }
        description="Atenção: esta ação apagará permanentemente o snapshot congelado deste período. O período voltará a ficar disponível para um novo freeze se necessário."
        maxWidth="sm"
      >
        <div className="space-y-4">
          <p className="text-sm">
            Confirma a exclusão definitiva do fechamento de{' '}
            <strong className="text-foreground">{fechamento.periodo_formatado}</strong>?
          </p>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <Button
              variant="outline"
              onClick={() => setModalExcluirAberto(false)}
              disabled={excluirMutation.isPending}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={() => excluirMutation.mutate()}
              disabled={excluirMutation.isPending}
            >
              {excluirMutation.isPending ? 'Excluindo...' : 'Confirmar Exclusão'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
