import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ArrowDownRight, ArrowUpRight, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react'
import { Modal } from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { api } from '@/api/client'

interface ProdutoSimples {
  id: number
  descricao: string
  quantidade: number
  quantidade_formatada: string
  unidade_simbolo: string
  status_estoque?: string
}

interface MovimentacaoModalProps {
  isOpen: boolean
  onClose: () => void
  produtoPadrao?: ProdutoSimples | null
  onSuccess?: () => void
}

const MOTIVOS_SAIDA = [
  { value: 'PRODUCAO', label: 'Uso em Produção / Consumo' },
  { value: 'AVARIA', label: 'Avaria / Defeito / Perda' },
  { value: 'VENCIMENTO', label: 'Vencimento / Descarte' },
  { value: 'AJUSTE', label: 'Ajuste de Inventário' },
  { value: 'OUTRO', label: 'Outro Motivo' },
]

const MOTIVOS_ENTRADA = [
  { value: 'COMPRA', label: 'Compra / Reposição de Estoque' },
  { value: 'DEVOLUCAO', label: 'Devolução de Material' },
  { value: 'AJUSTE', label: 'Ajuste de Inventário' },
  { value: 'OUTRO', label: 'Outro Motivo' },
]

export function MovimentacaoModal({
  isOpen,
  onClose,
  produtoPadrao,
  onSuccess,
}: MovimentacaoModalProps) {
  const queryClient = useQueryClient()

  const [produtoId, setProdutoId] = useState<number | ''>(produtoPadrao?.id || '')
  const [tipo, setTipo] = useState<'ENTRADA' | 'SAIDA'>('SAIDA')
  const [motivo, setMotivo] = useState('PRODUCAO')
  const [quantidadeStr, setQuantidadeStr] = useState('')
  const [observacao, setObservacao] = useState('')

  // Carrega produtos para o select se não houver produto pré-selecionado
  const { data: produtosData } = useQuery({
    queryKey: ['produtos-select'],
    queryFn: () => api.get<{ ok: boolean; itens: ProdutoSimples[] }>('/api/v1/produtos/?page_size=100&aba=TODOS'),
    enabled: isOpen && !produtoPadrao,
  })

  useEffect(() => {
    if (produtoPadrao?.id) {
      setProdutoId(produtoPadrao.id)
    } else {
      setProdutoId('')
    }
    setQuantidadeStr('')
    setObservacao('')
    setTipo('SAIDA')
    setMotivo('PRODUCAO')
  }, [produtoPadrao, isOpen])

  // Ajusta o motivo padrão ao alternar o tipo
  function handleTrocarTipo(novoTipo: 'ENTRADA' | 'SAIDA') {
    setTipo(novoTipo)
    setMotivo(novoTipo === 'ENTRADA' ? 'COMPRA' : 'PRODUCAO')
  }

  // Identifica o produto selecionado atualmente
  const produtoSelecionado =
    produtoPadrao ||
    produtosData?.itens?.find((p) => p.id === Number(produtoId))

  const quantidadeNum = parseFloat(quantidadeStr.replace(',', '.')) || 0
  const saldoAtual = produtoSelecionado?.quantidade ?? 0
  const unidade = produtoSelecionado?.unidade_simbolo || ''

  const novoSaldo =
    tipo === 'ENTRADA' ? saldoAtual + quantidadeNum : saldoAtual - quantidadeNum
  const saldoInsuficiente = tipo === 'SAIDA' && quantidadeNum > saldoAtual

  // Mutation de registro
  const mutation = useMutation({
    mutationFn: (body: any) => api.post('/api/v1/movimentacoes/registrar/', body),
    onSuccess: (res) => {
      toast.success(res.mensagem || 'Movimentação registrada com sucesso!', {
        description: `Novo saldo: ${res.saldo_atual || novoSaldo.toFixed(2)} ${unidade}`,
      })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['produtos'] })
      queryClient.invalidateQueries({ queryKey: ['movimentacoes'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
      onSuccess?.()
      onClose()
    },
    onError: (err: any) => {
      toast.error(err.message || 'Erro ao registrar movimentação.')
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!produtoId) {
      toast.warning('Selecione um produto.')
      return
    }
    if (quantidadeNum <= 0) {
      toast.warning('Informe uma quantidade maior que zero.')
      return
    }
    if (saldoInsuficiente) {
      toast.error('Saldo insuficiente para esta saída.')
      return
    }

    mutation.mutate({
      produto_id: produtoId,
      tipo,
      motivo,
      quantidade: quantidadeNum.toString(),
      observacao: observacao.trim(),
    })
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Registrar Movimentação Física"
      description="Entrada ou saída de material com recálculo automático de saldo."
      maxWidth="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Seleção do Tipo (Entrada / Saída) */}
        <div>
          <label className="text-xs font-semibold uppercase text-muted-foreground block mb-1.5">
            Tipo de Operação
          </label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => handleTrocarTipo('SAIDA')}
              className={`flex items-center justify-center gap-2 p-3 rounded-xl border text-sm font-semibold transition-all ${
                tipo === 'SAIDA'
                  ? 'bg-rose-500/10 border-rose-500 text-rose-700 dark:text-rose-400 shadow-xs'
                  : 'border-input bg-background hover:bg-muted text-muted-foreground'
              }`}
            >
              <ArrowUpRight className="w-4 h-4 text-rose-500" />
              <span>Saída (Consumo / Perda)</span>
            </button>

            <button
              type="button"
              onClick={() => handleTrocarTipo('ENTRADA')}
              className={`flex items-center justify-center gap-2 p-3 rounded-xl border text-sm font-semibold transition-all ${
                tipo === 'ENTRADA'
                  ? 'bg-emerald-500/10 border-emerald-500 text-emerald-700 dark:text-emerald-400 shadow-xs'
                  : 'border-input bg-background hover:bg-muted text-muted-foreground'
              }`}
            >
              <ArrowDownRight className="w-4 h-4 text-emerald-500" />
              <span>Entrada (Reposição)</span>
            </button>
          </div>
        </div>

        {/* Seleção de Produto */}
        <div>
          <label className="text-xs font-semibold uppercase text-muted-foreground block mb-1.5">
            Material / Insumo
          </label>
          {produtoPadrao ? (
            <div className="p-3 bg-muted/40 rounded-lg border border-border flex items-center justify-between">
              <div>
                <p className="font-semibold text-sm text-foreground">
                  {produtoPadrao.descricao}
                </p>
                <p className="text-xs text-muted-foreground">
                  Saldo em estoque: {produtoPadrao.quantidade_formatada}
                </p>
              </div>
              <Badge variant="outline">Pré-selecionado</Badge>
            </div>
          ) : (
            <select
              value={produtoId}
              onChange={(e) => setProdutoId(Number(e.target.value) || '')}
              className="w-full h-10 px-3 py-1 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              required
            >
              <option value="">Selecione um produto...</option>
              {produtosData?.itens?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.descricao} (Saldo: {p.quantidade_formatada})
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Motivo da Operação */}
        <div>
          <label className="text-xs font-semibold uppercase text-muted-foreground block mb-1.5">
            Motivo Auditável
          </label>
          <select
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            className="w-full h-10 px-3 py-1 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
            required
          >
            {(tipo === 'SAIDA' ? MOTIVOS_SAIDA : MOTIVOS_ENTRADA).map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </div>

        {/* Quantidade */}
        <div>
          <div className="flex justify-between items-center mb-1.5">
            <label className="text-xs font-semibold uppercase text-muted-foreground">
              Quantidade ({unidade || 'un'})
            </label>
            {produtoSelecionado && (
              <span className="text-xs text-muted-foreground">
                Saldo atual: <strong>{produtoSelecionado.quantidade_formatada}</strong>
              </span>
            )}
          </div>
          <Input
            type="number"
            step="0.01"
            min="0.01"
            placeholder="Ex: 10.50"
            value={quantidadeStr}
            onChange={(e) => setQuantidadeStr(e.target.value)}
            className="text-lg font-semibold"
            required
            autoFocus
          />
        </div>

        {/* Preview do Saldo Resultante */}
        {produtoSelecionado && quantidadeNum > 0 && (
          <div
            className={`p-3.5 rounded-xl border flex items-center justify-between text-sm transition-all ${
              saldoInsuficiente
                ? 'bg-rose-500/10 border-rose-500/30 text-rose-700 dark:text-rose-400'
                : 'bg-primary/5 border-primary/20 text-foreground'
            }`}
          >
            <div className="flex items-center gap-2.5">
              {saldoInsuficiente ? (
                <AlertCircle className="w-5 h-5 text-rose-500 shrink-0" />
              ) : (
                <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
              )}
              <div>
                <p className="font-semibold text-xs uppercase tracking-wider">
                  {saldoInsuficiente ? 'Saldo Insuficiente' : 'Estimativa Pós-Operação'}
                </p>
                <p className="text-xs mt-0.5 opacity-90">
                  {saldoAtual} {unidade} {tipo === 'ENTRADA' ? '+' : '-'} {quantidadeNum} {unidade} ={' '}
                  <strong className="font-mono text-sm font-bold">
                    {novoSaldo.toFixed(2)} {unidade}
                  </strong>
                </p>
              </div>
            </div>
            <Badge variant={saldoInsuficiente ? 'danger' : 'success'}>
              {saldoInsuficiente ? 'Bloqueado' : 'Válido'}
            </Badge>
          </div>
        )}

        {/* Observação Opcional */}
        <div>
          <label className="text-xs font-semibold uppercase text-muted-foreground block mb-1.5">
            Observação (Opcional)
          </label>
          <Input
            type="text"
            placeholder="Ex: O.S. #1420 ou Reposição Nota Fiscal"
            value={observacao}
            onChange={(e) => setObservacao(e.target.value)}
          />
        </div>

        {/* Botões de Ação */}
        <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="submit"
            disabled={mutation.isPending || saldoInsuficiente || !produtoId || quantidadeNum <= 0}
            className={`gap-2 min-w-32 ${
              tipo === 'SAIDA'
                ? 'bg-rose-600 hover:bg-rose-700 text-white'
                : 'bg-emerald-600 hover:bg-emerald-700 text-white'
            }`}
          >
            {mutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Registrando...</span>
              </>
            ) : (
              <span>Confirmar {tipo === 'ENTRADA' ? 'Entrada' : 'Saída'}</span>
            )}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
