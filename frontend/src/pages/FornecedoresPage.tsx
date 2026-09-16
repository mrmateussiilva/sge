import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Truck, Plus, Search, Trash2, Edit2, AlertCircle, Phone, Mail } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Modal } from '@/components/ui/modal'
import { FornecedorFormModal } from '@/components/fornecedores/FornecedorFormModal'
import type { FornecedorItem } from '@/types'

export function FornecedoresPage() {
  const queryClient = useQueryClient()
  const [busca, setBusca] = useState('')
  const [modalFormOpen, setModalFormOpen] = useState(false)
  const [fornecedorParaEditar, setFornecedorParaEditar] = useState<FornecedorItem | null>(null)
  const [fornecedorParaExcluir, setFornecedorParaExcluir] = useState<FornecedorItem | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['fornecedores'],
    queryFn: () => api.get<{ ok: boolean; itens: FornecedorItem[] }>('/api/v1/fornecedores/'),
  })

  const excluirMutation = useMutation({
    mutationFn: async (id: number) => {
      return api.post<{ ok: boolean; mensagem?: string; erro?: string; codigo?: string }>(
        `/api/v1/fornecedores/${id}/excluir/`,
        {}
      )
    },
    onSuccess: (res) => {
      if (res.ok) {
        toast.success(res.mensagem || 'Fornecedor excluído com sucesso!')
        queryClient.invalidateQueries({ queryKey: ['fornecedores'] })
        queryClient.invalidateQueries({ queryKey: ['produtos'] })
        queryClient.invalidateQueries({ queryKey: ['produtos_opcoes'] })
        setFornecedorParaExcluir(null)
      } else {
        toast.error(res.erro || 'Não foi possível excluir o fornecedor.')
      }
    },
    onError: (err: any) => {
      const msg = err.response?.data?.erro || err.message || 'Erro ao excluir fornecedor.'
      toast.error(msg)
    },
  })

  const itens = data?.itens || []
  const itensFiltrados = itens.filter((f) => {
    if (!busca.trim()) return true
    const termo = busca.toLowerCase()
    return (
      f.nome.toLowerCase().includes(termo) ||
      (f.cnpj && f.cnpj.toLowerCase().includes(termo)) ||
      (f.email && f.email.toLowerCase().includes(termo)) ||
      (f.telefone && f.telefone.toLowerCase().includes(termo))
    )
  })

  function abrirNovo() {
    setFornecedorParaEditar(null)
    setModalFormOpen(true)
  }

  function abrirEditar(f: FornecedorItem) {
    setFornecedorParaEditar(f)
    setModalFormOpen(true)
  }

  function confirmarExclusao() {
    if (fornecedorParaExcluir) {
      excluirMutation.mutate(fornecedorParaExcluir.id)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Gestão de Fornecedores</h1>
          <p className="text-sm text-muted-foreground">
            Cadastre parceiros, indústrias e fornecedores de insumos e matérias-primas.
          </p>
        </div>
        <Button onClick={abrirNovo} className="gap-1.5 self-start sm:self-auto shadow-xs">
          <Plus className="w-4 h-4" />
          <span>Novo Fornecedor</span>
        </Button>
      </div>

      {/* Busca e Estatísticas rápidas */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por nome, CNPJ, e-mail..."
            className="pl-9"
          />
        </div>
        <div className="text-xs text-muted-foreground self-end sm:self-auto">
          Total: <span className="font-semibold text-foreground">{itensFiltrados.length}</span> fornecedor(es)
        </div>
      </div>

      {/* Tabela de Fornecedores */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-12 text-center text-sm text-muted-foreground">
              Carregando fornecedores...
            </div>
          ) : itensFiltrados.length === 0 ? (
            <div className="p-12 text-center space-y-2">
              <Truck className="w-10 h-10 text-muted-foreground/60 mx-auto" />
              <p className="font-medium text-sm text-foreground">
                {busca ? 'Nenhum fornecedor encontrado para a busca' : 'Nenhum fornecedor cadastrado'}
              </p>
              <p className="text-xs text-muted-foreground">
                {busca ? 'Tente outros termos de pesquisa.' : 'Cadastre seu primeiro parceiro no botão acima.'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs uppercase bg-muted/50 text-muted-foreground border-b border-border">
                  <tr>
                    <th className="px-4 py-3.5 font-semibold">Fornecedor / Razão Social</th>
                    <th className="px-4 py-3.5 font-semibold">CNPJ</th>
                    <th className="px-4 py-3.5 font-semibold">Contato Direto</th>
                    <th className="px-4 py-3.5 font-semibold text-center">Insumos Vinculados</th>
                    <th className="px-4 py-3.5 font-semibold text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {itensFiltrados.map((f) => (
                    <tr key={f.id} className="hover:bg-muted/40 transition-colors">
                      <td className="px-4 py-3.5">
                        <div className="font-semibold text-foreground">{f.nome}</div>
                        {f.observacao && (
                          <div className="text-xs text-muted-foreground max-w-xs truncate" title={f.observacao}>
                            {f.observacao}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-muted-foreground font-mono text-xs">
                        {f.cnpj || '—'}
                      </td>
                      <td className="px-4 py-3.5 text-xs text-muted-foreground space-y-0.5">
                        {f.email && (
                          <div className="flex items-center gap-1 text-foreground/90">
                            <Mail className="w-3 h-3 text-muted-foreground" />
                            <span>{f.email}</span>
                          </div>
                        )}
                        {f.telefone && (
                          <div className="flex items-center gap-1 text-foreground/90">
                            <Phone className="w-3 h-3 text-muted-foreground" />
                            <span>{f.telefone}</span>
                          </div>
                        )}
                        {!f.email && !f.telefone && '—'}
                      </td>
                      <td className="px-4 py-3.5 text-center">
                        <Badge
                          variant={f.total_produtos > 0 ? 'secondary' : 'outline'}
                          className="font-medium"
                        >
                          {f.total_produtos} produto(s)
                        </Badge>
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => abrirEditar(f)}
                            className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                            title="Editar Fornecedor"
                          >
                            <Edit2 className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setFornecedorParaExcluir(f)}
                            className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                            title="Excluir Fornecedor"
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
      <FornecedorFormModal
        isOpen={modalFormOpen}
        onClose={() => setModalFormOpen(false)}
        fornecedor={fornecedorParaEditar}
      />

      {/* Modal Confirmação de Exclusão */}
      <Modal
        isOpen={Boolean(fornecedorParaExcluir)}
        onClose={() => setFornecedorParaExcluir(null)}
        title={
          <div className="flex items-center gap-2 text-destructive">
            <AlertCircle className="w-5 h-5" />
            <span>Excluir Fornecedor</span>
          </div>
        }
        description="Esta ação removerá o parceiro do cadastro. Se houver matérias-primas associadas a ele, o sistema bloqueará a exclusão para manter a rastreabilidade do estoque."
        maxWidth="sm"
      >
        <div className="space-y-4">
          <p className="text-sm">
            Deseja realmente excluir o fornecedor{' '}
            <strong className="text-foreground">{fornecedorParaExcluir?.nome}</strong>?
          </p>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <Button
              variant="outline"
              onClick={() => setFornecedorParaExcluir(null)}
              disabled={excluirMutation.isPending}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={confirmarExclusao}
              disabled={excluirMutation.isPending}
            >
              {excluirMutation.isPending ? 'Excluindo...' : 'Excluir Fornecedor'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
