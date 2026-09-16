import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Tags, Palette } from 'lucide-react'
import { api } from '@/api/client'
import { Modal } from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { CategoriaItem } from '@/types'

interface CategoriaFormModalProps {
  isOpen: boolean
  onClose: () => void
  categoria?: CategoriaItem | null
}

const CORES_PALETA = [
  { hex: '#6366F1', label: 'Índigo' },
  { hex: '#3B82F6', label: 'Azul' },
  { hex: '#06B6D4', label: 'Ciano' },
  { hex: '#10B981', label: 'Esmeralda' },
  { hex: '#84CC16', label: 'Lima' },
  { hex: '#F59E0B', label: 'Âmbar' },
  { hex: '#EF4444', label: 'Vermelho' },
  { hex: '#EC4899', label: 'Rosa' },
  { hex: '#8B5CF6', label: 'Roxo' },
  { hex: '#64748B', label: 'Ardósia' },
]

export function CategoriaFormModal({
  isOpen,
  onClose,
  categoria,
}: CategoriaFormModalProps) {
  const queryClient = useQueryClient()
  const isEditing = Boolean(categoria?.id)

  const [nome, setNome] = useState('')
  const [descricao, setDescricao] = useState('')
  const [cor, setCor] = useState('#6366F1')
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    if (categoria) {
      setNome(categoria.nome || '')
      setDescricao(categoria.descricao || '')
      setCor(categoria.cor || '#6366F1')
    } else {
      setNome('')
      setDescricao('')
      setCor('#6366F1')
    }
    setErro(null)
  }, [categoria, isOpen])

  const salvarMutation = useMutation({
    mutationFn: async () => {
      const url = isEditing
        ? `/api/v1/categorias/${categoria!.id}/editar/`
        : '/api/v1/categorias/salvar/'
      return api.post<{ ok: boolean; id?: number; erro?: string }>(url, {
        nome: nome.trim(),
        descricao: descricao.trim(),
        cor: cor.trim(),
      })
    },
    onSuccess: (res) => {
      if (res.ok) {
        toast.success(
          isEditing
            ? 'Categoria atualizada com sucesso!'
            : 'Categoria criada com sucesso!'
        )
        queryClient.invalidateQueries({ queryKey: ['categorias'] })
        queryClient.invalidateQueries({ queryKey: ['produtos'] })
        queryClient.invalidateQueries({ queryKey: ['produtos_opcoes'] })
        onClose()
      } else {
        setErro(res.erro || 'Erro ao salvar categoria.')
        toast.error(res.erro || 'Erro ao salvar categoria.')
      }
    },
    onError: (err: any) => {
      const msg = err.response?.data?.erro || err.message || 'Erro inesperado ao salvar.'
      setErro(msg)
      toast.error(msg)
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!nome.trim()) {
      setErro('O nome da categoria é obrigatório.')
      return
    }
    setErro(null)
    salvarMutation.mutate()
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <Tags className="w-5 h-5 text-primary" />
          <span>{isEditing ? 'Editar Categoria' : 'Nova Categoria'}</span>
        </div>
      }
      description={
        isEditing
          ? 'Atualize o nome, cor de identificação e descrição do grupo de insumos.'
          : 'Cadastre uma nova categoria para classificar matérias-primas e produtos.'
      }
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {erro && (
          <div className="p-3 text-xs rounded-lg bg-destructive/10 text-destructive border border-destructive/20 font-medium">
            {erro}
          </div>
        )}

        {/* Pré-visualização da Categoria */}
        <div className="p-3.5 rounded-lg bg-muted/40 border border-border/70 flex items-center justify-between">
          <span className="text-xs text-muted-foreground font-medium">Pré-visualização:</span>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-md border text-sm font-semibold shadow-xs"
               style={{ backgroundColor: `${cor}15`, borderColor: `${cor}40`, color: cor }}>
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: cor }} />
            <span>{nome.trim() || 'Nome da Categoria'}</span>
          </div>
        </div>

        {/* Nome */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-foreground">
            Nome da Categoria <span className="text-destructive">*</span>
          </label>
          <Input
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            placeholder="Ex: Tecidos Sintéticos, Tintas Sublimáticas..."
            required
            autoFocus
          />
        </div>

        {/* Descrição */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-foreground">
            Descrição <span className="text-xs text-muted-foreground font-normal">(Opcional)</span>
          </label>
          <Input
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            placeholder="Detalhes ou finalidade da categoria..."
          />
        </div>

        {/* Seletor de Cor */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <Palette className="w-3.5 h-3.5 text-muted-foreground" />
              Cor de Destaque
            </label>
            <span className="font-mono text-xs text-muted-foreground">{cor.toUpperCase()}</span>
          </div>

          {/* Paleta rápida */}
          <div className="grid grid-cols-5 gap-2">
            {CORES_PALETA.map((item) => {
              const isSelected = cor.toUpperCase() === item.hex.toUpperCase()
              return (
                <button
                  key={item.hex}
                  type="button"
                  title={item.label}
                  onClick={() => setCor(item.hex)}
                  className={`h-8 rounded-lg flex items-center justify-center transition-all border ${
                    isSelected
                      ? 'ring-2 ring-primary ring-offset-2 scale-105 border-transparent'
                      : 'border-border/60 hover:scale-102 hover:border-border'
                  }`}
                  style={{ backgroundColor: item.hex }}
                >
                  {isSelected && (
                    <span className="w-2 h-2 rounded-full bg-white shadow-xs" />
                  )}
                </button>
              )
            })}
          </div>

          {/* Seletor personalizado */}
          <div className="flex items-center gap-2 pt-1">
            <input
              type="color"
              id="cor-picker"
              value={cor}
              onChange={(e) => setCor(e.target.value)}
              className="w-8 h-8 rounded border border-border cursor-pointer p-0 bg-transparent"
            />
            <label htmlFor="cor-picker" className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
              Escolher cor personalizada no espectro
            </label>
          </div>
        </div>

        {/* Ações */}
        <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={salvarMutation.isPending}
          >
            Cancelar
          </Button>
          <Button type="submit" disabled={salvarMutation.isPending}>
            {salvarMutation.isPending ? 'Salvando...' : isEditing ? 'Salvar Alterações' : 'Criar Categoria'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
