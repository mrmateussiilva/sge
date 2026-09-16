import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Loader2, Calculator, Info } from 'lucide-react'
import { Modal } from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { api } from '@/api/client'
import type { ProdutoItem } from '@/types'

interface OpcoesProduto {
  ok: boolean
  tipos_produto: Array<{ value: string; label: string }>
  unidades_medida: Array<{ value: string; label: string }>
  tipos_tinta: Array<{ value: string; label: string }>
  cores_tinta: Array<{ value: string; label: string }>
  fornecedores: Array<{ id: number; nome: string }>
  categorias: Array<{ id: number; nome: string; cor: string }>
}

interface ProdutoFormModalProps {
  isOpen: boolean
  onClose: () => void
  produtoParaEditar?: ProdutoItem | null
  onSuccess?: () => void
}

export function ProdutoFormModal({
  isOpen,
  onClose,
  produtoParaEditar,
  onSuccess,
}: ProdutoFormModalProps) {
  const queryClient = useQueryClient()
  const isEditing = Boolean(produtoParaEditar)

  // Opções de selects
  const { data: opcoes } = useQuery({
    queryKey: ['opcoes-produto'],
    queryFn: () => api.get<OpcoesProduto>('/api/v1/produtos/opcoes/'),
    enabled: isOpen,
  })

  // Campos do formulário
  const [descricao, setDescricao] = useState('')
  const [tipoProduto, setTipoProduto] = useState('PAPEL')
  const [unidadeMedida, setUnidadeMedida] = useState('M')
  const [fornecedorId, setFornecedorId] = useState('')
  const [categoriaId, setCategoriaId] = useState('')
  const [quantidadeBase, setQuantidadeBase] = useState('')
  const [estoqueMinimo, setEstoqueMinimo] = useState('')
  const [precoCusto, setPrecoCusto] = useState('')
  const [precoVenda, setPrecoVenda] = useState('')
  const [metrosPorRolo, setMetrosPorRolo] = useState('')
  const [tipoTinta, setTipoTinta] = useState('N/A')
  const [corTinta, setCorTinta] = useState('INCOLOR')
  const [litrosPorVidro, setLitrosPorVidro] = useState('')

  // Popula campos ao abrir para edição ou resetar
  useEffect(() => {
    if (produtoParaEditar) {
      setDescricao(produtoParaEditar.descricao || '')
      setTipoProduto(produtoParaEditar.tipo_produto || 'PAPEL')
      setUnidadeMedida(produtoParaEditar.tipo_produto === 'TINTA' ? 'L' : ['PAPEL', 'TECIDO'].includes(produtoParaEditar.tipo_produto) ? 'M' : 'UN')
      setFornecedorId(produtoParaEditar.fornecedor ? '' : '') // id pode ser recuperado ou selecionado
      setCategoriaId('')
      setQuantidadeBase(produtoParaEditar.quantidade ? String(produtoParaEditar.quantidade) : '')
      setEstoqueMinimo(produtoParaEditar.estoque_minimo ? String(produtoParaEditar.estoque_minimo) : '')
      setPrecoCusto(produtoParaEditar.preco_custo ? String(produtoParaEditar.preco_custo) : '')
      setPrecoVenda(produtoParaEditar.preco_venda ? String(produtoParaEditar.preco_venda) : '')
      setMetrosPorRolo(produtoParaEditar.metros_por_rolo ? String(produtoParaEditar.metros_por_rolo) : '')
      setTipoTinta(produtoParaEditar.tipo_tinta || 'N/A')
      setCorTinta(produtoParaEditar.cor_tinta || 'INCOLOR')
      setLitrosPorVidro(produtoParaEditar.litros_por_vidro ? String(produtoParaEditar.litros_por_vidro) : '')
    } else {
      setDescricao('')
      setTipoProduto('PAPEL')
      setUnidadeMedida('M')
      setFornecedorId('')
      setCategoriaId('')
      setQuantidadeBase('')
      setEstoqueMinimo('')
      setPrecoCusto('')
      setPrecoVenda('')
      setMetrosPorRolo('')
      setTipoTinta('N/A')
      setCorTinta('INCOLOR')
      setLitrosPorVidro('')
    }
  }, [produtoParaEditar, isOpen])

  // Ajusta unidade base recomendada ao mudar o tipo
  function handleTipoChange(novoTipo: string) {
    setTipoProduto(novoTipo)
    if (['PAPEL', 'TECIDO'].includes(novoTipo)) {
      setUnidadeMedida('M')
    } else if (novoTipo === 'TINTA') {
      setUnidadeMedida('L')
    } else {
      setUnidadeMedida('UN')
    }
  }

  // Cálculos de margem em tempo real
  const custoNum = parseFloat(precoCusto.replace(',', '.')) || 0
  const vendaNum = parseFloat(precoVenda.replace(',', '.')) || 0
  const lucroNum = vendaNum > 0 && custoNum > 0 ? vendaNum - custoNum : null
  const margemMarkup = lucroNum !== null && custoNum > 0 ? (lucroNum / custoNum) * 100 : null

  // Mutation para salvar (criar ou editar)
  const mutation = useMutation({
    mutationFn: (body: any) => {
      if (isEditing && produtoParaEditar?.id) {
        return api.post(`/api/v1/produtos/${produtoParaEditar.id}/editar/`, body)
      }
      return api.post('/api/v1/produtos/cadastrar/', body)
    },
    onSuccess: () => {
      toast.success(
        isEditing ? 'Produto atualizado com sucesso!' : 'Produto cadastrado com sucesso!'
      )
      queryClient.invalidateQueries({ queryKey: ['produtos'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
      onSuccess?.()
      onClose()
    },
    onError: (err: any) => {
      toast.error(err.message || 'Erro ao salvar produto.')
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!descricao.trim()) {
      toast.warning('A descrição do produto é obrigatória.')
      return
    }

    const payload: Record<string, any> = {
      descricao: descricao.trim(),
      tipo_produto: tipoProduto,
      unidade_medida: unidadeMedida,
      fornecedor_id: fornecedorId ? Number(fornecedorId) : null,
      categoria_id: categoriaId ? Number(categoriaId) : null,
      quantidade_base: quantidadeBase ? quantidadeBase.replace(',', '.') : '0',
      estoque_minimo: estoqueMinimo ? estoqueMinimo.replace(',', '.') : null,
      preco_custo: precoCusto ? precoCusto.replace(',', '.') : null,
      preco_venda: precoVenda ? precoVenda.replace(',', '.') : null,
      metros_por_rolo: metrosPorRolo ? metrosPorRolo.replace(',', '.') : null,
      tipo_tinta: tipoTinta,
      cor_tinta: corTinta,
      litros_por_vidro: litrosPorVidro ? litrosPorVidro.replace(',', '.') : null,
    }

    mutation.mutate(payload)
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? `Editar: ${produtoParaEditar?.descricao}` : 'Cadastrar Novo Insumo'}
      description="Preencha os dados do material, especificações e precificação."
      maxWidth="xl"
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Seção 1: Dados Principais */}
        <div className="space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground border-b border-border pb-1">
            1. Identificação Geral
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="text-xs font-semibold text-muted-foreground block mb-1">
                Descrição do Insumo *
              </label>
              <Input
                placeholder="Ex: Papel Sublimático 90g Bobina 1,60m"
                value={descricao}
                onChange={(e) => setDescricao(e.target.value)}
                required
                autoFocus
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">
                Tipo de Insumo *
              </label>
              <select
                value={tipoProduto}
                onChange={(e) => handleTipoChange(e.target.value)}
                className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                required
              >
                {opcoes?.tipos_produto?.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">
                Unidade Base de Estoque *
              </label>
              <select
                value={unidadeMedida}
                onChange={(e) => setUnidadeMedida(e.target.value)}
                className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                required
              >
                {opcoes?.unidades_medida?.map((u) => (
                  <option key={u.value} value={u.value}>
                    {u.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">
                Fornecedor Vinculado
              </label>
              <select
                value={fornecedorId}
                onChange={(e) => setFornecedorId(e.target.value)}
                className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="">Sem fornecedor selecionado</option>
                {opcoes?.fornecedores?.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.nome}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">
                Categoria
              </label>
              <select
                value={categoriaId}
                onChange={(e) => setCategoriaId(e.target.value)}
                className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="">Sem categoria</option>
                {opcoes?.categorias?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nome}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Seção 2: Controle de Estoque */}
        <div className="space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground border-b border-border pb-1">
            2. Controle de Estoque
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">
                {isEditing ? 'Ajustar Saldo Atual' : 'Saldo Inicial'} ({unidadeMedida})
              </label>
              <Input
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                value={quantidadeBase}
                onChange={(e) => setQuantidadeBase(e.target.value)}
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">
                Estoque Mínimo de Alerta ({unidadeMedida})
              </label>
              <Input
                type="number"
                step="0.01"
                min="0"
                placeholder="Ex: 50.00"
                value={estoqueMinimo}
                onChange={(e) => setEstoqueMinimo(e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Seção 3: Especificações Condicionais */}
        {['PAPEL', 'TECIDO'].includes(tipoProduto) && (
          <div className="space-y-4 bg-muted/20 p-3.5 rounded-lg border border-border/80">
            <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-primary" />
              <span>Especificação Física: Rolos / Bobinas</span>
            </h4>
            <div className="max-w-xs">
              <label className="text-xs font-semibold text-muted-foreground block mb-1">
                Metros por Rolo (Estimativa)
              </label>
              <Input
                type="number"
                step="0.01"
                min="0"
                placeholder="Ex: 100"
                value={metrosPorRolo}
                onChange={(e) => setMetrosPorRolo(e.target.value)}
              />
            </div>
          </div>
        )}

        {tipoProduto === 'TINTA' && (
          <div className="space-y-4 bg-muted/20 p-3.5 rounded-lg border border-border/80">
            <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-primary" />
              <span>Especificação de Tinta</span>
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Tipo de Tinta
                </label>
                <select
                  value={tipoTinta}
                  onChange={(e) => setTipoTinta(e.target.value)}
                  className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  {opcoes?.tipos_tinta?.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Cor da Tinta
                </label>
                <select
                  value={corTinta}
                  onChange={(e) => setCorTinta(e.target.value)}
                  className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  {opcoes?.cores_tinta?.map((c) => (
                    <option key={c.value} value={c.value}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Litros por Frasco/Vidro
                </label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="Ex: 1.00"
                  value={litrosPorVidro}
                  onChange={(e) => setLitrosPorVidro(e.target.value)}
                />
              </div>
            </div>
          </div>
        )}

        {/* Seção 4: Precificação & Simulador de Margem */}
        <div className="space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground border-b border-border pb-1">
            4. Precificação & Lucratividade
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">
                Preço de Custo (R$)
              </label>
              <Input
                type="number"
                step="0.01"
                min="0"
                placeholder="Ex: 15.50"
                value={precoCusto}
                onChange={(e) => setPrecoCusto(e.target.value)}
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">
                Preço de Venda (R$)
              </label>
              <Input
                type="number"
                step="0.01"
                min="0"
                placeholder="Ex: 28.00"
                value={precoVenda}
                onChange={(e) => setPrecoVenda(e.target.value)}
              />
            </div>
          </div>

          {/* Simulador de Markup em tempo real */}
          {custoNum > 0 && vendaNum > 0 && (
            <div className="p-3 bg-primary/5 rounded-xl border border-primary/20 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <Calculator className="w-4 h-4 text-primary" />
                <span>
                  Lucro Unitário:{' '}
                  <strong>
                    {new Intl.NumberFormat('pt-BR', {
                      style: 'currency',
                      currency: 'BRL',
                    }).format(lucroNum || 0)}
                  </strong>
                </span>
              </div>
              <span className="font-semibold text-primary">
                Margem Markup: {margemMarkup !== null ? `${margemMarkup.toFixed(1)}%` : '—'}
              </span>
            </div>
          )}
        </div>

        {/* Botões do Rodapé */}
        <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={mutation.isPending} className="gap-2">
            {mutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Salvando...</span>
              </>
            ) : (
              <span>{isEditing ? 'Salvar Alterações' : 'Cadastrar Insumo'}</span>
            )}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
