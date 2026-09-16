import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Lock, AlertTriangle, CheckCircle2, Calculator } from 'lucide-react'
import { api } from '@/api/client'
import { Modal } from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface FechamentoNovoModalProps {
  isOpen: boolean
  onClose: () => void
  periodoSugerido?: {
    data_inicio: string
    data_fim: string
    periodo_formatado: string
  }
}

export function FechamentoNovoModal({
  isOpen,
  onClose,
  periodoSugerido,
}: FechamentoNovoModalProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [dataInicio, setDataInicio] = useState('')
  const [dataFim, setDataFim] = useState('')
  const [observacao, setObservacao] = useState('')

  useEffect(() => {
    if (periodoSugerido && isOpen) {
      setDataInicio(periodoSugerido.data_inicio)
      setDataFim(periodoSugerido.data_fim)
      setObservacao('')
    }
  }, [periodoSugerido, isOpen])

  // Prévia e validação de período
  const datasPreenchidas = Boolean(dataInicio && dataFim)
  const { data: revisaoData, isLoading: revisando } = useQuery({
    queryKey: ['fechamento_revisao', dataInicio, dataFim],
    queryFn: () =>
      api.get<{ ok: boolean; resumo?: any; erro?: string }>(
        `/api/v1/fechamentos/revisar/?data_inicio=${dataInicio}&data_fim=${dataFim}`
      ),
    enabled: isOpen && datasPreenchidas,
  })

  const resumo = revisaoData?.resumo
  const duplicado = Boolean(resumo?.duplicado)

  const congelarMutation = useMutation({
    mutationFn: async () => {
      return api.post<{ ok: boolean; id?: number; mensagem?: string; erro?: string }>(
        '/api/v1/fechamentos/realizar/',
        {
          data_inicio: dataInicio,
          data_fim: dataFim,
          observacao: observacao.trim(),
        }
      )
    },
    onSuccess: (res) => {
      if (res.ok && res.id) {
        toast.success(res.mensagem || 'Fechamento de estoque realizado com sucesso!')
        queryClient.invalidateQueries({ queryKey: ['fechamentos'] })
        onClose()
        navigate(`/fechamentos/${res.id}`)
      } else {
        toast.error(res.erro || 'Erro ao realizar fechamento.')
      }
    },
    onError: (err: any) => {
      const msg = err.response?.data?.erro || err.message || 'Erro inesperado ao congelar.'
      toast.error(msg)
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!dataInicio || !dataFim) {
      toast.error('Informe as datas inicial e final do fechamento.')
      return
    }
    if (duplicado) {
      toast.error('Já existe um fechamento para este período.')
      return
    }
    congelarMutation.mutate()
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <Lock className="w-5 h-5 text-primary" />
          <span>Novo Fechamento de Estoque</span>
        </div>
      }
      description="Gere um snapshot histórico imutável das quantidades físicas e custos de todos os itens do inventário no encerramento do período."
      maxWidth="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Datas */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">
              Data Inicial <span className="text-destructive">*</span>
            </label>
            <Input
              type="date"
              value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
              required
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">
              Data Final <span className="text-destructive">*</span>
            </label>
            <Input
              type="date"
              value={dataFim}
              onChange={(e) => setDataFim(e.target.value)}
              required
            />
          </div>
        </div>

        {/* Card de Revisão / Valuation Prévia */}
        {datasPreenchidas && (
          <div className="rounded-xl border border-border bg-muted/30 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <Calculator className="w-4 h-4 text-primary" />
                Prévia do Inventário Congelado
              </span>
              {revisando && (
                <span className="text-xs text-muted-foreground animate-pulse">
                  Calculando valuation...
                </span>
              )}
            </div>

            {duplicado ? (
              <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs space-y-1">
                <div className="flex items-center gap-1.5 font-semibold">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>Período já encerrado anteriormente</span>
                </div>
                <p>
                  Já existe um fechamento oficial registrado para o período de{' '}
                  <strong>{resumo?.periodo_formatado}</strong>. Não é permitido sobrescrever snapshots congelados.
                </p>
              </div>
            ) : resumo ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div className="p-2.5 rounded-lg bg-card border border-border/70">
                    <span className="text-[11px] text-muted-foreground block">Total de Insumos</span>
                    <span className="text-base font-bold text-foreground">
                      {resumo.total_itens} itens
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-card border border-border/70">
                    <span className="text-[11px] text-muted-foreground block">Valuation de Custo</span>
                    <span className="text-base font-bold text-foreground valor-sensivel">
                      {resumo.valor_total_formatado}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-card border border-border/70 col-span-2 sm:col-span-1">
                    <span className="text-[11px] text-muted-foreground block">Integridade de Custos</span>
                    {resumo.produtos_sem_custo > 0 ? (
                      <span className="text-xs font-semibold text-amber-600 dark:text-amber-400">
                        {resumo.produtos_sem_custo} item(ns) sem custo
                      </span>
                    ) : (
                      <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> 100% precificado
                      </span>
                    )}
                  </div>
                </div>

                {resumo.produtos_sem_custo > 0 && (
                  <p className="text-[11px] text-muted-foreground">
                    * Insumos com saldo em estoque sem preço de custo cadastrado serão gravados no snapshot sem valuation financeiro.
                  </p>
                )}
              </div>
            ) : null}
          </div>
        )}

        {/* Observações */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-foreground">
            Anotações / Observações do Período <span className="text-xs text-muted-foreground font-normal">(Opcional)</span>
          </label>
          <textarea
            value={observacao}
            onChange={(e) => setObservacao(e.target.value)}
            placeholder="Ex: Fechamento mensal de competência fiscal. Inventário físico validado pela equipe do galpão."
            rows={2}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-colors resize-none"
          />
        </div>

        {/* Ações */}
        <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={congelarMutation.isPending}
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            disabled={congelarMutation.isPending || duplicado || !datasPreenchidas}
            className="gap-1.5"
          >
            <Lock className="w-4 h-4" />
            <span>
              {congelarMutation.isPending ? 'Congelando Estoque...' : 'Efetivar Fechamento'}
            </span>
          </Button>
        </div>
      </form>
    </Modal>
  )
}
