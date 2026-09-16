import { useQuery } from '@tanstack/react-query'
import { ArrowDownRight, ArrowUpRight } from 'lucide-react'
import { api } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function RelatoriosPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['relatorio'],
    queryFn: () => api.get<any>('/api/v1/relatorio/'),
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Relatório de Movimentações</h1>
        <p className="text-sm text-muted-foreground">
          Consolidação de entradas, saídas e saldos de insumos no período.
        </p>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Carregando relatório...</p>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                  Total Entradas no Período
                </CardTitle>
                <ArrowDownRight className="w-4 h-4 text-emerald-500" />
              </CardHeader>
              <CardContent>
                <div className="text-sm space-y-1">
                  {data?.totais_entradas?.map((t: any, i: number) => (
                    <div key={i} className="flex justify-between py-1 border-b border-border/50">
                      <span className="text-muted-foreground">{t.nome}:</span>
                      <span className="font-semibold">{t.total_formatado}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-semibold text-rose-600 dark:text-rose-400">
                  Total Saídas no Período
                </CardTitle>
                <ArrowUpRight className="w-4 h-4 text-rose-500" />
              </CardHeader>
              <CardContent>
                <div className="text-sm space-y-1">
                  {data?.totais_saidas?.map((t: any, i: number) => (
                    <div key={i} className="flex justify-between py-1 border-b border-border/50">
                      <span className="text-muted-foreground">{t.nome}:</span>
                      <span className="font-semibold">{t.total_formatado}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Produtos Afetados no Período</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase bg-muted/50 text-muted-foreground border-b border-border">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Produto</th>
                      <th className="px-4 py-3 font-semibold">Entradas</th>
                      <th className="px-4 py-3 font-semibold">Saídas</th>
                      <th className="px-4 py-3 font-semibold">Variação Líquida</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data?.produtos_afetados?.map((item: any, idx: number) => (
                      <tr key={idx} className="hover:bg-muted/40 transition-colors">
                        <td className="px-4 py-3 font-medium">{item.nome}</td>
                        <td className="px-4 py-3 text-emerald-600 dark:text-emerald-400 font-mono">
                          +{item.entradas_formatadas}
                        </td>
                        <td className="px-4 py-3 text-rose-600 dark:text-rose-400 font-mono">
                          -{item.saidas_formatadas}
                        </td>
                        <td className="px-4 py-3 font-bold font-mono">
                          {item.saldo_formatado}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
