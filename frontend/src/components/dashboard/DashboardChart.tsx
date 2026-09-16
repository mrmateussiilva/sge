import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart3, PieChart, Calendar } from 'lucide-react'
import { api } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

interface ChartResponse {
  ok: boolean
  ano_selecionado: number
  anos_disponiveis: number[]
  mensal: {
    meses: string[]
    entradas: number[]
    saidas: number[]
  }
  por_tipo: Array<{
    tipo: string
    label: string
    valor: number
    valor_formatado: string
    percentual: number
  }>
}

const CORES_TIPOS = [
  'bg-blue-500',
  'bg-emerald-500',
  'bg-purple-500',
  'bg-amber-500',
  'bg-rose-500',
  'bg-cyan-500',
]

export function DashboardChart() {
  const [ano, setAno] = useState<number | ''>('')

  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-chart', ano],
    queryFn: () => {
      const url = ano ? `/api/v1/dashboard/chart/?ano=${ano}` : '/api/v1/dashboard/chart/'
      return api.get<ChartResponse>(url)
    },
  })

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 h-80 animate-pulse bg-muted/40" />
        <Card className="h-80 animate-pulse bg-muted/40" />
      </div>
    )
  }

  const mensal = data?.mensal
  const meses = mensal?.meses || []
  const entradas = mensal?.entradas || []
  const saidas = mensal?.saidas || []

  // Calcula o valor máximo para escala do gráfico de barras
  const maxVal = Math.max(...entradas, ...saidas, 1)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Gráfico de Barras: Entradas e Saídas Mensais */}
      <Card className="lg:col-span-2">
        <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 gap-2">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-primary" />
              <span>Fluxo de Movimentações Mensais</span>
            </CardTitle>
            <CardDescription>
              Comparativo de volumes de entrada e saída por mês
            </CardDescription>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            {/* Seletor de Ano */}
            <div className="flex items-center gap-1.5 text-xs bg-muted/50 px-2 py-1 rounded-lg border border-border">
              <Calendar className="w-3.5 h-3.5 text-muted-foreground" />
              <select
                value={ano || data?.ano_selecionado || ''}
                onChange={(e) => setAno(Number(e.target.value))}
                className="bg-transparent font-semibold text-foreground focus:outline-none cursor-pointer"
              >
                {data?.anos_disponiveis?.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
            </div>

            {/* Legendas */}
            <div className="flex items-center gap-3 text-xs pl-2 border-l border-border">
              <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                <span className="w-2.5 h-2.5 rounded-xs bg-emerald-500 inline-block" />
                Entradas
              </span>
              <span className="flex items-center gap-1 text-rose-600 dark:text-rose-400 font-medium">
                <span className="w-2.5 h-2.5 rounded-xs bg-rose-500 inline-block" />
                Saídas
              </span>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {/* Container Gráfico de Barras Responsivo */}
          <div className="h-60 w-full pt-4 flex items-end gap-1.5 sm:gap-3 border-b border-border pb-2">
            {meses.map((mes, idx) => {
              const qtdEntrada = entradas[idx] || 0
              const qtdSaida = saidas[idx] || 0
              const alturaEntrada = Math.round((qtdEntrada / maxVal) * 100)
              const alturaSaida = Math.round((qtdSaida / maxVal) * 100)

              return (
                <div key={mes} className="flex-1 flex flex-col items-center h-full justify-end group relative">
                  {/* Tooltip Hover */}
                  <div className="absolute -top-12 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-popover text-popover-foreground text-[11px] py-1 px-2 rounded-md shadow-lg border border-border pointer-events-none z-20 whitespace-nowrap">
                    <p className="font-bold text-center">{mes}</p>
                    <p className="text-emerald-500">+{qtdEntrada} entradas</p>
                    <p className="text-rose-500">-{qtdSaida} saídas</p>
                  </div>

                  {/* Barras Lado a Lado */}
                  <div className="w-full flex items-end justify-center gap-0.5 sm:gap-1 h-full pb-1">
                    {/* Barra de Entrada */}
                    <div
                      style={{ height: `${Math.max(alturaEntrada, 2)}%` }}
                      className="w-1/2 max-w-[12px] bg-emerald-500 hover:bg-emerald-600 rounded-t-xs transition-all duration-300"
                    />
                    {/* Barra de Saída */}
                    <div
                      style={{ height: `${Math.max(alturaSaida, 2)}%` }}
                      className="w-1/2 max-w-[12px] bg-rose-500 hover:bg-rose-600 rounded-t-xs transition-all duration-300"
                    />
                  </div>

                  {/* Rótulo do Mês */}
                  <span className="text-[10px] sm:text-xs text-muted-foreground font-medium mt-1">
                    {mes}
                  </span>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Distribuição de Patrimônio por Insumo */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <PieChart className="w-4 h-4 text-primary" />
            <span>Patrimônio por Categoria</span>
          </CardTitle>
          <CardDescription>Distribuição financeira do estoque atual</CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {data?.por_tipo?.length === 0 ? (
            <p className="text-xs text-muted-foreground py-8 text-center">
              Sem dados financeiros de estoque no momento.
            </p>
          ) : (
            <div className="space-y-3">
              {/* Barra Progressiva Segmentada */}
              <div className="h-3 w-full rounded-full overflow-hidden flex bg-muted">
                {data?.por_tipo?.map((item, idx) => (
                  <div
                    key={item.tipo}
                    style={{ width: `${item.percentual}%` }}
                    className={`${CORES_TIPOS[idx % CORES_TIPOS.length]} transition-all duration-500`}
                    title={`${item.label}: ${item.percentual}% (${item.valor_formatado})`}
                  />
                ))}
              </div>

              {/* Lista Detalhada */}
              <div className="divide-y divide-border/60 text-xs">
                {data?.por_tipo?.map((item, idx) => (
                  <div key={item.tipo} className="py-2 flex items-center justify-between first:pt-1">
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className={`w-2.5 h-2.5 rounded-full shrink-0 ${CORES_TIPOS[idx % CORES_TIPOS.length]}`}
                      />
                      <span className="font-medium text-foreground truncate">{item.label}</span>
                    </div>

                    <div className="text-right shrink-0">
                      <span className="valor-sensivel font-semibold block text-foreground">
                        {item.valor_formatado}
                      </span>
                      <span className="text-[10px] text-muted-foreground">
                        {item.percentual}% do total
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
