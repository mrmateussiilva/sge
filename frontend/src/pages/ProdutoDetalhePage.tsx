import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft,
  ArrowLeftRight,
  Edit,
  Boxes,
  Truck,
  DollarSign,
  TrendingUp,
  Activity,
  Layers,
} from 'lucide-react'
import { api } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { MovimentacaoModal } from '@/components/movimentacoes/MovimentacaoModal'
import { ProdutoFormModal } from '@/components/produtos/ProdutoFormModal'

export function ProdutoDetalhePage() {
  const { id } = useParams<{ id: string }>()
  const [modalMovOpen, setModalMovOpen] = useState(false)
  const [modalEditOpen, setModalEditOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<'movimentacoes' | 'precos'>('movimentacoes')

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['produto-detalhe', id],
    queryFn: () => api.get<any>(`/api/v1/produtos/${id}/`),
    enabled: Boolean(id),
  })

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-48 bg-muted rounded" />
        <div className="h-44 bg-muted/40 rounded-xl" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="h-48 bg-muted/40 rounded-xl" />
          <div className="h-48 bg-muted/40 rounded-xl" />
        </div>
      </div>
    )
  }

  const p = data?.produto
  const movimentacoes = data?.movimentacoes || []
  const historicoPrecos = data?.historico_precos || []

  if (!p) {
    return (
      <div className="text-center py-16 space-y-4">
        <Boxes className="w-12 h-12 text-muted-foreground mx-auto" />
        <h2 className="text-lg font-bold">Produto não encontrado</h2>
        <Button asChild variant="outline">
          <Link to="/produtos">Voltar para a lista</Link>
        </Button>
      </div>
    )
  }

  // Cálculo da saúde de estoque em relação ao mínimo
  const percentualMinimo =
    p.estoque_minimo && p.estoque_minimo > 0
      ? Math.min(Math.round((p.quantidade / p.estoque_minimo) * 100), 100)
      : 100

  // Valor total imobilizado
  const valorTotalImobilizado =
    p.preco_custo !== null ? p.quantidade * p.preco_custo : null

  return (
    <div className="space-y-6">
      {/* Top Bar Back Link */}
      <div className="flex items-center justify-between">
        <Button asChild variant="ghost" size="sm" className="gap-1.5 text-muted-foreground">
          <Link to="/produtos">
            <ArrowLeft className="w-4 h-4" />
            <span>Voltar ao catálogo</span>
          </Link>
        </Button>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => setModalEditOpen(true)}
          >
            <Edit className="w-4 h-4" />
            <span>Editar</span>
          </Button>

          <Button
            size="sm"
            className="gap-1.5 bg-primary shadow-sm"
            onClick={() => setModalMovOpen(true)}
          >
            <ArrowLeftRight className="w-4 h-4" />
            <span>Movimentar Estoque</span>
          </Button>
        </div>
      </div>

      {/* Hero Panel */}
      <Card className="border-border shadow-sm overflow-hidden">
        <div className="p-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{p.tipo_label}</Badge>
                {p.categoria && (
                  <Badge variant="secondary" style={{ borderLeftColor: p.categoria.cor }}>
                    {p.categoria.nome}
                  </Badge>
                )}
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
                    ? 'Estoque Zerado'
                    : p.status_estoque === 'BAIXO'
                    ? 'Estoque Baixo'
                    : 'Estoque Normal'}
                </Badge>
              </div>

              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
                {p.descricao}
              </h1>

              <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                <Truck className="w-3.5 h-3.5" />
                <span>Fornecedor: {p.fornecedor?.nome || 'Não associado'}</span>
              </p>
            </div>

            {/* Saldo Hero */}
            <div className="flex flex-col sm:items-end justify-center bg-muted/30 p-4 rounded-xl border border-border/80 min-w-48">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Saldo Físico Atual
              </span>
              <div className="text-3xl sm:text-4xl font-extrabold tracking-tight text-primary mt-1">
                {p.quantidade_formatada}
              </div>
              {p.embalagens_estimadas > 0 && (
                <span className="text-xs text-muted-foreground mt-0.5">
                  ≈ {p.embalagens_estimadas}{' '}
                  {p.tipo_produto === 'TINTA' ? 'garrafas/vidros' : 'bobinas/rolos'}
                </span>
              )}
            </div>
          </div>

          {/* Barra de Saúde do Estoque */}
          {p.estoque_minimo !== null && p.estoque_minimo > 0 && (
            <div className="mt-6 pt-5 border-t border-border">
              <div className="flex justify-between items-center text-xs mb-1.5 font-medium">
                <span className="text-muted-foreground">
                  Nível em relação ao mínimo ({p.estoque_minimo} {p.unidade_simbolo}):
                </span>
                <span
                  className={`font-semibold ${
                    p.status_estoque === 'ZERADO'
                      ? 'text-rose-600'
                      : p.status_estoque === 'BAIXO'
                      ? 'text-amber-600'
                      : 'text-emerald-600'
                  }`}
                >
                  {p.quantidade} / {p.estoque_minimo} {p.unidade_simbolo} ({percentualMinimo}%)
                </span>
              </div>
              <div className="w-full h-2.5 bg-muted rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 rounded-full ${
                    p.status_estoque === 'ZERADO'
                      ? 'bg-rose-500'
                      : p.status_estoque === 'BAIXO'
                      ? 'bg-amber-500'
                      : 'bg-emerald-500'
                  }`}
                  style={{ width: `${percentualMinimo}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Grid de Especificações & Financeiro */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Card 1: Especificações do Insumo */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Layers className="w-4 h-4 text-primary" />
              <span>Especificações do Material</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm divide-y divide-border/60">
            <div className="flex justify-between pt-1">
              <span className="text-muted-foreground">Unidade de Medida Base:</span>
              <span className="font-semibold">{p.unidade_nome} ({p.unidade_simbolo})</span>
            </div>

            {p.metros_por_rolo && (
              <div className="flex justify-between pt-2">
                <span className="text-muted-foreground">Comprimento por Rolo:</span>
                <span className="font-semibold">{p.metros_por_rolo} metros</span>
              </div>
            )}

            {p.tipo_produto === 'TINTA' && (
              <>
                <div className="flex justify-between pt-2">
                  <span className="text-muted-foreground">Tipo da Tinta:</span>
                  <span className="font-semibold">{p.tipo_tinta}</span>
                </div>
                <div className="flex justify-between pt-2">
                  <span className="text-muted-foreground">Cor:</span>
                  <span className="font-semibold">{p.cor_tinta}</span>
                </div>
                {p.litros_por_vidro && (
                  <div className="flex justify-between pt-2">
                    <span className="text-muted-foreground">Volume por Vidro:</span>
                    <span className="font-semibold">{p.litros_por_vidro} L</span>
                  </div>
                )}
              </>
            )}

            <div className="flex justify-between pt-2">
              <span className="text-muted-foreground">Fornecedor Principal:</span>
              <span className="font-semibold">{p.fornecedor?.nome || 'Não vinculado'}</span>
            </div>
          </CardContent>
        </Card>

        {/* Card 2: Gestão Financeira & Margem */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-emerald-600" />
              <span>Gestão Financeira & Margem</span>
            </CardTitle>
            <CardDescription>
              Valores unitários e patrimônio imobilizado
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm divide-y divide-border/60">
            <div className="flex justify-between pt-1">
              <span className="text-muted-foreground">Preço de Custo Unitário:</span>
              <span className="font-semibold valor-sensivel">{p.preco_custo_formatado}</span>
            </div>

            <div className="flex justify-between pt-2">
              <span className="text-muted-foreground">Preço de Venda Unitário:</span>
              <span className="font-semibold valor-sensivel">{p.preco_venda_formatado}</span>
            </div>

            <div className="flex justify-between pt-2">
              <span className="text-muted-foreground">Lucro Bruto Unitário:</span>
              <span className="font-semibold valor-sensivel text-emerald-600 dark:text-emerald-400">
                {p.lucro !== null
                  ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(p.lucro)
                  : '—'}
              </span>
            </div>

            <div className="flex justify-between pt-2">
              <span className="text-muted-foreground">Margem Markup:</span>
              <span className="font-bold valor-sensivel text-primary">
                {p.margem !== null ? `${p.margem.toFixed(1)}%` : '—'}
              </span>
            </div>

            <div className="flex justify-between pt-2">
              <span className="text-muted-foreground">Total Imobilizado em Estoque:</span>
              <span className="font-bold valor-sensivel text-foreground">
                {valorTotalImobilizado !== null
                  ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valorTotalImobilizado)
                  : '—'}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Histórico: Abas de Movimentações e Preços */}
      <Card>
        <CardHeader className="p-0 border-b border-border">
          <div className="flex items-center px-4 pt-2 gap-2">
            <button
              onClick={() => setActiveTab('movimentacoes')}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-all ${
                activeTab === 'movimentacoes'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <Activity className="w-4 h-4" />
              <span>Histórico de Movimentações ({movimentacoes.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('precos')}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-all ${
                activeTab === 'precos'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <TrendingUp className="w-4 h-4" />
              <span>Histórico de Preços ({historicoPrecos.length})</span>
            </button>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {activeTab === 'movimentacoes' ? (
            movimentacoes.length === 0 ? (
              <div className="p-8 text-center text-sm text-muted-foreground">
                Nenhuma movimentação registrada para este produto.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase bg-muted/40 text-muted-foreground border-b border-border">
                    <tr>
                      <th className="px-4 py-3">Tipo</th>
                      <th className="px-4 py-3">Quantidade</th>
                      <th className="px-4 py-3">Motivo</th>
                      <th className="px-4 py-3">Usuário</th>
                      <th className="px-4 py-3">Data / Hora</th>
                      <th className="px-4 py-3">Observação</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {movimentacoes.map((mov: any) => {
                      const isEntrada = mov.tipo === 'ENTRADA'
                      return (
                        <tr key={mov.id} className="hover:bg-muted/30">
                          <td className="px-4 py-2.5">
                            <Badge variant={isEntrada ? 'success' : 'danger'}>
                              {mov.tipo_display}
                            </Badge>
                          </td>
                          <td className="px-4 py-2.5 font-mono font-bold">
                            {isEntrada ? '+' : '-'}
                            {mov.quantidade_formatada}
                          </td>
                          <td className="px-4 py-2.5 text-muted-foreground">
                            {mov.motivo_display || '—'}
                          </td>
                          <td className="px-4 py-2.5 text-muted-foreground">{mov.usuario}</td>
                          <td className="px-4 py-2.5 text-muted-foreground whitespace-nowrap text-xs">
                            {mov.data_formatada}
                          </td>
                          <td className="px-4 py-2.5 text-muted-foreground text-xs truncate max-w-xs">
                            {mov.observacao || '—'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )
          ) : (
            historicoPrecos.length === 0 ? (
              <div className="p-8 text-center text-sm text-muted-foreground">
                Nenhum histórico de alteração de preço registrado.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase bg-muted/40 text-muted-foreground border-b border-border">
                    <tr>
                      <th className="px-4 py-3">Data / Hora</th>
                      <th className="px-4 py-3">Usuário</th>
                      <th className="px-4 py-3">Custo Anterior</th>
                      <th className="px-4 py-3">Novo Custo</th>
                      <th className="px-4 py-3">Venda Anterior</th>
                      <th className="px-4 py-3">Nova Venda</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {historicoPrecos.map((hp: any) => (
                      <tr key={hp.id} className="hover:bg-muted/30">
                        <td className="px-4 py-2.5 text-xs text-muted-foreground whitespace-nowrap">
                          {hp.data_formatada}
                        </td>
                        <td className="px-4 py-2.5 text-muted-foreground">{hp.usuario}</td>
                        <td className="px-4 py-2.5 valor-sensivel text-muted-foreground line-through">
                          {hp.preco_custo_antigo_formatado}
                        </td>
                        <td className="px-4 py-2.5 valor-sensivel font-semibold text-emerald-600 dark:text-emerald-400">
                          {hp.preco_custo_novo_formatado}
                        </td>
                        <td className="px-4 py-2.5 valor-sensivel text-muted-foreground line-through">
                          {hp.preco_venda_antigo_formatado}
                        </td>
                        <td className="px-4 py-2.5 valor-sensivel font-semibold text-primary">
                          {hp.preco_venda_novo_formatado}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}
        </CardContent>
      </Card>

      {/* Modal de Movimentação */}
      <MovimentacaoModal
        isOpen={modalMovOpen}
        onClose={() => setModalMovOpen(false)}
        produtoPadrao={p}
        onSuccess={refetch}
      />

      {/* Modal de Edição */}
      <ProdutoFormModal
        isOpen={modalEditOpen}
        onClose={() => setModalEditOpen(false)}
        produtoParaEditar={p}
        onSuccess={refetch}
      />
    </div>
  )
}
