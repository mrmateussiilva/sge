import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Plus, Trash2, Loader2, Calculator } from 'lucide-react'
import { Modal } from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { api } from '@/api/client'

interface ItemLinha {
  produto_id: string
  quantidade: string
  preco_unitario: string
}

interface FornecedorSimples {
  id: number
  nome: string
}

interface ProdutoSimples {
  id: number
  descricao: string
  preco_custo: number | null
  unidade_simbolo: string
}

interface OrdemFormModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
}

export function OrdemFormModal({ isOpen, onClose, onSuccess }: OrdemFormModalProps) {
  const queryClient = useQueryClient()

  const [fornecedorId, setFornecedorId] = useState('')
  const [observacao, setObservacao] = useState('')
  const [itens, setItens] = useState<ItemLinha[]>([
    { produto_id: '', quantidade: '1', preco_unitario: '' },
  ])

  // Carrega fornecedores e produtos para os selects
  const { data: fornecedoresData } = useQuery({
    queryKey: ['fornecedores-select'],
    queryFn: () => api.get<{ ok: boolean; itens: FornecedorSimples[] }>('/api/v1/fornecedores/'),
    enabled: isOpen,
  })

  const { data: produtosData } = useQuery({
    queryKey: ['produtos-select-ordens'],
    queryFn: () => api.get<{ ok: boolean; itens: ProdutoSimples[] }>('/api/v1/produtos/?page_size=100&aba=TODOS'),
    enabled: isOpen,
  })

  useEffect(() => {
    if (isOpen) {
      setFornecedorId('')
      setObservacao('')
      setItens([{ produto_id: '', quantidade: '1', preco_unitario: '' }])
    }
  }, [isOpen])

  function handleAddItem() {
    setItens((prev) => [...prev, { produto_id: '', quantidade: '1', preco_unitario: '' }])
  }

  function handleRemoveItem(idx: number) {
    setItens((prev) => prev.filter((_, i) => i !== idx))
  }

  function handleItemChange(idx: number, campo: keyof ItemLinha, valor: string) {
    setItens((prev) => {
      const copy = [...prev]
      copy[idx] = { ...copy[idx], [campo]: valor }

      // Se alterou o produto, preenche o preço unitário padrão se disponível
      if (campo === 'produto_id') {
        const prod = produtosData?.itens?.find((p) => p.id === Number(valor))
        if (prod && prod.preco_custo !== null) {
          copy[idx].preco_unitario = String(prod.preco_custo)
        }
      }
      return copy
    })
  }

  // Cálculo do valor total em tempo real
  const totalOrdem = itens.reduce((acc, item) => {
    const q = parseFloat(item.quantidade.replace(',', '.')) || 0
    const p = parseFloat(item.preco_unitario.replace(',', '.')) || 0
    return acc + q * p
  }, 0)

  const mutation = useMutation({
    mutationFn: (body: any) => api.post('/api/v1/ordens/criar/', body),
    onSuccess: (res) => {
      toast.success(`Ordem de compra #${res.id} criada com sucesso!`)
      queryClient.invalidateQueries({ queryKey: ['ordens'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
      onSuccess?.()
      onClose()
    },
    onError: (err: any) => {
      toast.error(err.message || 'Erro ao criar ordem de compra.')
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    const itensValidos = itens.filter(
      (it) => it.produto_id && parseFloat(it.quantidade.replace(',', '.')) > 0
    )

    if (itensValidos.length === 0) {
      toast.warning('Adicione pelo menos um item válido na ordem.')
      return
    }

    const payload = {
      fornecedor_id: fornecedorId ? Number(fornecedorId) : null,
      observacao: observacao.trim(),
      itens: itensValidos.map((it) => ({
        produto_id: Number(it.produto_id),
        quantidade: it.quantidade.replace(',', '.'),
        preco_unitario: it.preco_unitario ? it.preco_unitario.replace(',', '.') : '0',
      })),
    }

    mutation.mutate(payload)
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Nova Ordem de Compra"
      description="Gere um pedido formal a fornecedores com itens e quantidades."
      maxWidth="2xl"
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-semibold text-muted-foreground block mb-1">
              Fornecedor
            </label>
            <select
              value={fornecedorId}
              onChange={(e) => setFornecedorId(e.target.value)}
              className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            >
              <option value="">Selecione um fornecedor...</option>
              {fornecedoresData?.itens?.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-muted-foreground block mb-1">
              Observações / Referência
            </label>
            <Input
              placeholder="Ex: Pedido ref. reposição mensal ou NF 8452"
              value={observacao}
              onChange={(e) => setObservacao(e.target.value)}
            />
          </div>
        </div>

        {/* Lista Dinâmica de Itens */}
        <div className="space-y-3">
          <div className="flex items-center justify-between border-b border-border pb-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Itens do Pedido ({itens.length})
            </h4>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleAddItem}
              className="h-7 text-xs gap-1"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Adicionar Linha</span>
            </Button>
          </div>

          <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
            {itens.map((item, idx) => {
              const q = parseFloat(item.quantidade.replace(',', '.')) || 0
              const p = parseFloat(item.preco_unitario.replace(',', '.')) || 0
              const subtotal = q * p

              return (
                <div
                  key={idx}
                  className="grid grid-cols-12 gap-2 items-center p-2.5 rounded-lg border border-border bg-muted/20 text-sm"
                >
                  <div className="col-span-5">
                    <select
                      value={item.produto_id}
                      onChange={(e) => handleItemChange(idx, 'produto_id', e.target.value)}
                      className="w-full h-8 px-2 rounded-md border border-input bg-background text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                      required
                    >
                      <option value="">Selecione o insumo...</option>
                      {produtosData?.itens?.map((prod) => (
                        <option key={prod.id} value={prod.id}>
                          {prod.descricao}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="col-span-2">
                    <Input
                      type="number"
                      step="0.01"
                      min="0.01"
                      placeholder="Qtd"
                      value={item.quantidade}
                      onChange={(e) => handleItemChange(idx, 'quantidade', e.target.value)}
                      className="h-8 text-xs font-semibold"
                      required
                    />
                  </div>

                  <div className="col-span-2">
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="Preço R$"
                      value={item.preco_unitario}
                      onChange={(e) => handleItemChange(idx, 'preco_unitario', e.target.value)}
                      className="h-8 text-xs font-semibold"
                    />
                  </div>

                  <div className="col-span-2 text-right text-xs font-mono font-bold text-foreground truncate">
                    {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(subtotal)}
                  </div>

                  <div className="col-span-1 text-right">
                    {itens.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleRemoveItem(idx)}
                        className="text-muted-foreground hover:text-destructive p-1 rounded transition-colors"
                        title="Remover linha"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Rodapé com Valor Total */}
          <div className="p-3 bg-muted/40 rounded-lg border border-border flex items-center justify-between text-sm">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Calculator className="w-4 h-4 text-primary" />
              <span>Total acumulado da ordem:</span>
            </div>
            <div className="font-extrabold text-base text-primary">
              {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totalOrdem)}
            </div>
          </div>
        </div>

        {/* Ações */}
        <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={mutation.isPending} className="gap-2">
            {mutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Criando Ordem...</span>
              </>
            ) : (
              <span>Criar Ordem de Compra</span>
            )}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
