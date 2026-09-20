import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Tags, Plus, Search, Trash2, Edit2, AlertCircle } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { useDebounce } from '@/hooks/useDebounce'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Modal } from '@/components/ui/modal'
import { CategoriaFormModal } from '@/components/categorias/CategoriaFormModal'
import type { CategoriaItem } from '@/types'

export function CategoriasPage() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [busca, setBusca] = useState(searchParams.get('busca') || '')
  const debouncedBusca = useDebounce(busca, 350)

  const [modalFormOpen, setModalFormOpen] = useState(false)
  const [categoriaParaEditar, setCategoriaParaEditar] = useState<CategoriaItem | null>(null)
  const [categoriaParaExcluir, setCategoriaParaExcluir] = useState<CategoriaItem | null>(null)

  // Sincroniza busca na URL sem poluir o histórico
  useEffect(() => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (debouncedBusca) {
          next.set('busca', debouncedBusca)
        } else {
          next.delete('busca')
        }
        return next
      },
      { replace: true }
    )
  }, [debouncedBusca, setSearchParams])

  const { data, isLoading } = useQuery({
    queryKey: ['categorias'],
    queryFn: () => api.get<{ ok: boolean; itens: CategoriaItem[] }>('/api/v1/categorias/'),
  })

  const excluirMutation = useMutation({
    mutationFn: async (id: number) => {
      return api.post<{ ok: boolean; mensagem?: string; erro?: string; codigo?: string }>(
        `/api/v1/categorias/${id}/excluir/`,
        {}
      )
    },
    onSuccess: (res) => {
      if (res.ok) {
        toast.success(res.mensagem || 'Categoria excluída com sucesso!')
        queryClient.invalidateQueries({ queryKey: ['categorias'] })
        queryClient.invalidateQueries({ queryKey: ['produtos'] })
        queryClient.invalidateQueries({ queryKey: ['produtos_opcoes'] })
        setCategoriaParaExcluir(null)
      } else {
        toast.error(res.erro || 'Não foi possível excluir a categoria.')
      }
    },
    onError: (err: any) => {
      const msg = err.response?.data?.erro || err.message || 'Erro ao excluir categoria.'
      toast.error(msg)
    },
  })

  const itens = data?.itens || []
  const itensFiltrados = itens.filter((c) => {
    if (!busca.trim()) return true
    const termo = busca.toLowerCase()
    return (
      c.nome.toLowerCase().includes(termo) ||
      (c.descricao && c.descricao.toLowerCase().includes(termo))
    )
  })

  function abrirNovo() {
    setCategoriaParaEditar(null)
    setModalFormOpen(true)
  }

  function abrirEditar(c: CategoriaItem) {
    setCategoriaParaEditar(c)
    setModalFormOpen(true)
  }

  function confirmarExclusao() {
    if (categoriaParaExcluir) {
      excluirMutation.mutate(categoriaParaExcluir.id)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Categorias de Insumos</h1>
          <p className="text-sm text-muted-foreground">
            Classifique materiais por grupos para relatórios, agrupamentos e filtros de estoque.
          </p>
        </div>
        <Button onClick={abrirNovo} className="gap-1.5 self-start sm:self-auto shadow-xs">
          <Plus className="w-4 h-4" />
          <span>Nova Categoria</span>
        </Button>
      </div>

      {/* Busca e Estatísticas rápidas */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por nome ou descrição..."
            className="pl-9"
          />
        </div>
        <div className="text-xs text-muted-foreground self-end sm:self-auto">
          Total: <span className="font-semibold text-foreground">{itensFiltrados.length}</span> categoria(s)
        </div>
      </div>

      {/* Tabela de Categorias */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-12 text-center text-sm text-muted-foreground">
              Carregando categorias...
            </div>
          ) : itensFiltrados.length === 0 ? (
            <div className="p-12 text-center space-y-2">
              <Tags className="w-10 h-10 text-muted-foreground/60 mx-auto" />
              <p className="font-medium text-sm text-foreground">
                {busca ? 'Nenhuma categoria encontrada para a busca' : 'Nenhuma categoria cadastrada'}
              </p>
              <p className="text-xs text-muted-foreground">
                {busca ? 'Tente outros termos de pesquisa.' : 'Crie sua primeira categoria no botão acima.'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs uppercase bg-muted/50 text-muted-foreground border-b border-border">
                  <tr>
                    <th className="px-4 py-3.5 font-semibold">Cor & Grupo</th>
                    <th className="px-4 py-3.5 font-semibold">Descrição</th>
                    <th className="px-4 py-3.5 font-semibold text-center">Itens Vinculados</th>
                    <th className="px-4 py-3.5 font-semibold text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {itensFiltrados.map((c) => (
                    <tr key={c.id} className="hover:bg-muted/40 transition-colors">
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-2.5">
                          <span
                            className="w-4 h-4 rounded-full border border-black/10 shrink-0 shadow-2xs"
                            style={{ backgroundColor: c.cor }}
                          />
                          <div>
                            <span className="font-semibold text-foreground">{c.nome}</span>
                            <span className="block font-mono text-[10px] text-muted-foreground">
                              {c.cor.toUpperCase()}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-muted-foreground max-w-xs truncate">
                        {c.descricao || '—'}
                      </td>
                      <td className="px-4 py-3.5 text-center">
                        <Badge
                          variant={c.total_produtos > 0 ? 'secondary' : 'outline'}
                          className="font-medium"
                        >
                          {c.total_produtos} produto(s)
                        </Badge>
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => abrirEditar(c)}
                            className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                            title="Editar Categoria"
                          >
                            <Edit2 className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setCategoriaParaExcluir(c)}
                            className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                            title="Excluir Categoria"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modal Formulário (Criar / Editar) */}
      <CategoriaFormModal
        isOpen={modalFormOpen}
        onClose={() => setModalFormOpen(false)}
        categoria={categoriaParaEditar}
      />

      {/* Modal Confirmação de Exclusão */}
      <Modal
        isOpen={Boolean(categoriaParaExcluir)}
        onClose={() => setCategoriaParaExcluir(null)}
        title={
          <div className="flex items-center gap-2 text-destructive">
            <AlertCircle className="w-5 h-5" />
            <span>Excluir Categoria</span>
          </div>
        }
        description="Esta ação removerá a categoria do catálogo. Se houver produtos associados, o sistema impedirá a exclusão para preservar a integridade dos dados."
        maxWidth="sm"
      >
        <div className="space-y-4">
          <p className="text-sm">
            Deseja realmente excluir a categoria{' '}
            <strong className="text-foreground">{categoriaParaExcluir?.nome}</strong>?
          </p>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <Button
              variant="outline"
              onClick={() => setCategoriaParaExcluir(null)}
              disabled={excluirMutation.isPending}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={confirmarExclusao}
              disabled={excluirMutation.isPending}
            >
              {excluirMutation.isPending ? 'Excluindo...' : 'Excluir Categoria'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
