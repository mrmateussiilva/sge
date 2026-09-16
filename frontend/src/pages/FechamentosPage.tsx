import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Lock, Plus, ArrowRight, CheckCircle2, AlertTriangle, Calendar } from 'lucide-react'
import { api } from '@/api/client'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { FechamentoNovoModal } from '@/components/fechamentos/FechamentoNovoModal'

export function FechamentosPage() {
  const [modalNovoAberto, setModalNovoAberto] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['fechamentos'],
    queryFn: () => api.get<any>('/api/v1/fechamentos/'),
  })

  const itens = data?.itens || []
  const periodoSugerido = data?.periodo_sugerido

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Fechamento Mensal de Estoque</h1>
          <p className="text-sm text-muted-foreground">
            Snapshots históricos imutáveis do saldo físico e valuation em datas congeladas para auditoria e contabilidade.
          </p>
        </div>
        <Button
          onClick={() => setModalNovoAberto(true)}
          className="gap-1.5 self-start sm:self-auto shadow-xs"
        >
          <Plus className="w-4 h-4" />
          <span>Novo Fechamento</span>
        </Button>
      </div>

      {/* Lista de Fechamentos Históricos */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-12 text-center text-sm text-muted-foreground">
              Carregando histórico de fechamentos...
            </div>
          ) : itens.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <Lock className="w-10 h-10 text-muted-foreground/60 mx-auto" />
              <p className="font-semibold text-sm text-foreground">Nenhum fechamento registrado</p>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                Efetue o fechamento mensal para congelar o valuation e gerar o relatório oficial de inventário.
              </p>
              <Button
                size="sm"
                onClick={() => setModalNovoAberto(true)}
                className="gap-1.5 mt-2"
              >
                <Plus className="w-4 h-4" />
                <span>Iniciar Primeiro Fechamento</span>
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs uppercase bg-muted/50 text-muted-foreground border-b border-border">
                  <tr>
                    <th className="px-4 py-3.5 font-semibold">Período de Competência</th>
                    <th className="px-4 py-3.5 font-semibold text-center">Itens no Snapshot</th>
                    <th className="px-4 py-3.5 font-semibold text-right">Valuation Total (Custo)</th>
                    <th className="px-4 py-3.5 font-semibold text-center">Status dos Custos</th>
                    <th className="px-4 py-3.5 font-semibold">Realizado por</th>
                    <th className="px-4 py-3.5 font-semibold">Data do Freeze</th>
                    <th className="px-4 py-3.5 font-semibold text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {itens.map((f: any) => (
                    <tr
                      key={f.id}
                      className="hover:bg-muted/40 transition-colors group cursor-pointer"
                    >
                      <td className="px-4 py-3.5 font-semibold text-foreground">
                        <Link
                          to={`/fechamentos/${f.id}`}
                          className="flex items-center gap-2 hover:text-primary transition-colors"
                        >
                          <Calendar className="w-4 h-4 text-muted-foreground group-hover:text-primary" />
                          <span>{f.periodo_formatado}</span>
                        </Link>
                      </td>
                      <td className="px-4 py-3.5 text-center text-muted-foreground">
                        <Badge variant="outline" className="font-mono text-xs">
                          {f.total_itens} item(ns)
                        </Badge>
                      </td>
                      <td className="px-4 py-3.5 text-right font-semibold valor-sensivel text-foreground">
                        {f.valor_total_formatado}
                      </td>
                      <td className="px-4 py-3.5 text-center">
                        {f.calculo_completo ? (
                          <span className="inline-flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Completo
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400 font-medium">
                            <AlertTriangle className="w-3.5 h-3.5" /> {f.produtos_sem_custo} s/ custo
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-muted-foreground text-xs">
                        {f.usuario}
                      </td>
                      <td className="px-4 py-3.5 text-muted-foreground whitespace-nowrap text-xs">
                        {f.data_fechamento_formatada}
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <Button
                          asChild
                          variant="ghost"
                          size="sm"
                          className="h-8 gap-1 text-xs text-muted-foreground group-hover:text-foreground"
                        >
                          <Link to={`/fechamentos/${f.id}`}>
                            <span>Abrir</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </Link>
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modal Novo Fechamento */}
      <FechamentoNovoModal
        isOpen={modalNovoAberto}
        onClose={() => setModalNovoAberto(false)}
        periodoSugerido={periodoSugerido}
      />
    </div>
  )
}
