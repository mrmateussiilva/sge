import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Truck } from 'lucide-react'
import { api } from '@/api/client'
import { Modal } from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { FornecedorItem } from '@/types'

interface FornecedorFormModalProps {
  isOpen: boolean
  onClose: () => void
  fornecedor?: FornecedorItem | null
}

export function FornecedorFormModal({
  isOpen,
  onClose,
  fornecedor,
}: FornecedorFormModalProps) {
  const queryClient = useQueryClient()
  const isEditing = Boolean(fornecedor?.id)

  const [nome, setNome] = useState('')
  const [cnpj, setCnpj] = useState('')
  const [email, setEmail] = useState('')
  const [telefone, setTelefone] = useState('')
  const [observacao, setObservacao] = useState('')
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    if (fornecedor) {
      setNome(fornecedor.nome || '')
      setCnpj(fornecedor.cnpj || '')
      setEmail(fornecedor.email || '')
      setTelefone(fornecedor.telefone || '')
      setObservacao(fornecedor.observacao || '')
    } else {
      setNome('')
      setCnpj('')
      setEmail('')
      setTelefone('')
      setObservacao('')
    }
    setErro(null)
  }, [fornecedor, isOpen])

  const salvarMutation = useMutation({
    mutationFn: async () => {
      const url = isEditing
        ? `/api/v1/fornecedores/${fornecedor!.id}/editar/`
        : '/api/v1/fornecedores/salvar/'
      return api.post<{ ok: boolean; id?: number; erro?: string }>(url, {
        nome: nome.trim(),
        cnpj: cnpj.trim(),
        email: email.trim(),
        telefone: telefone.trim(),
        observacao: observacao.trim(),
      })
    },
    onSuccess: (res) => {
      if (res.ok) {
        toast.success(
          isEditing
            ? 'Fornecedor atualizado com sucesso!'
            : 'Fornecedor cadastrado com sucesso!'
        )
        queryClient.invalidateQueries({ queryKey: ['fornecedores'] })
        queryClient.invalidateQueries({ queryKey: ['produtos'] })
        queryClient.invalidateQueries({ queryKey: ['produtos_opcoes'] })
        onClose()
      } else {
        setErro(res.erro || 'Erro ao salvar fornecedor.')
        toast.error(res.erro || 'Erro ao salvar fornecedor.')
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
      setErro('O nome da empresa ou razão social é obrigatório.')
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
          <Truck className="w-5 h-5 text-primary" />
          <span>{isEditing ? 'Editar Fornecedor' : 'Novo Fornecedor'}</span>
        </div>
      }
      description={
        isEditing
          ? 'Atualize os dados de contato e faturamento do fornecedor.'
          : 'Cadastre um novo fornecedor de insumos e matérias-primas.'
      }
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {erro && (
          <div className="p-3 text-xs rounded-lg bg-destructive/10 text-destructive border border-destructive/20 font-medium">
            {erro}
          </div>
        )}

        {/* Nome */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-foreground">
            Razão Social / Nome Fantasia <span className="text-destructive">*</span>
          </label>
          <Input
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            placeholder="Ex: Têxtil Brasil Ltda, Tintas & Co..."
            required
            autoFocus
          />
        </div>

        {/* CNPJ */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-foreground">
            CNPJ <span className="text-xs text-muted-foreground font-normal">(Opcional)</span>
          </label>
          <Input
            value={cnpj}
            onChange={(e) => setCnpj(e.target.value)}
            placeholder="00.000.000/0000-00"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* E-mail */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">
              E-mail de Contato
            </label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="comercial@fornecedor.com"
            />
          </div>

          {/* Telefone */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">
              Telefone / WhatsApp
            </label>
            <Input
              value={telefone}
              onChange={(e) => setTelefone(e.target.value)}
              placeholder="(11) 99999-9999"
            />
          </div>
        </div>

        {/* Observações */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-foreground">
            Observações Comerciais <span className="text-xs text-muted-foreground font-normal">(Condições, chave PIX, etc)</span>
          </label>
          <textarea
            value={observacao}
            onChange={(e) => setObservacao(e.target.value)}
            placeholder="Ex: Prazo padrão de entrega: 5 dias úteis. Condição: 30 dias boleto."
            rows={3}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-colors resize-none"
          />
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
            {salvarMutation.isPending ? 'Salvando...' : isEditing ? 'Salvar Alterações' : 'Cadastrar Fornecedor'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
