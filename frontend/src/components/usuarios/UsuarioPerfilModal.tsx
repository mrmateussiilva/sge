import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ShieldAlert, UserCheck, Shield } from 'lucide-react'
import { api } from '@/api/client'
import { Modal } from '@/components/ui/modal'
import { Button } from '@/components/ui/button'

interface UsuarioPerfilModalProps {
  isOpen: boolean
  onClose: () => void
  usuario: {
    id: number
    username: string
    email: string
    is_active: boolean
    is_superuser: boolean
    perfil: string
    grupo_id: number | null
  } | null
  perfis: Array<{ id: number; nome: string; interno: string }>
}

export function UsuarioPerfilModal({
  isOpen,
  onClose,
  usuario,
  perfis,
}: UsuarioPerfilModalProps) {
  const queryClient = useQueryClient()

  const [grupoId, setGrupoId] = useState<string>('')
  const [isActive, setIsActive] = useState(true)
  const [isSuperuser, setIsSuperuser] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    if (usuario && isOpen) {
      setGrupoId(usuario.grupo_id ? String(usuario.grupo_id) : '')
      setIsActive(usuario.is_active)
      setIsSuperuser(usuario.is_superuser)
      setErro(null)
    }
  }, [usuario, isOpen])

  const atualizarMutation = useMutation({
    mutationFn: async () => {
      return api.post<{ ok: boolean; mensagem?: string; erro?: string }>(
        `/api/v1/usuarios/${usuario!.id}/perfil/`,
        {
          grupo_id: grupoId ? Number(grupoId) : null,
          is_active: isActive,
          is_superuser: isSuperuser,
        }
      )
    },
    onSuccess: (res) => {
      if (res.ok) {
        toast.success(res.mensagem || 'Usuário atualizado com sucesso!')
        queryClient.invalidateQueries({ queryKey: ['usuarios'] })
        onClose()
      } else {
        setErro(res.erro || 'Erro ao atualizar usuário.')
        toast.error(res.erro || 'Erro ao atualizar usuário.')
      }
    },
    onError: (err: any) => {
      const msg = err.response?.data?.erro || err.message || 'Erro inesperado ao atualizar usuário.'
      setErro(msg)
      toast.error(msg)
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setErro(null)
    atualizarMutation.mutate()
  }

  if (!usuario) return null

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <UserCheck className="w-5 h-5 text-primary" />
          <span>Gerenciar Acesso: {usuario.username}</span>
        </div>
      }
      description="Modifique as permissões de grupo, privilégios administrativos e status de ativação da conta."
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {erro && (
          <div className="p-3 text-xs rounded-lg bg-destructive/10 text-destructive border border-destructive/20 font-medium flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 shrink-0" />
            <span>{erro}</span>
          </div>
        )}

        <div className="p-3 rounded-lg bg-muted/40 border border-border/70 text-xs space-y-1">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Usuário:</span>
            <span className="font-semibold text-foreground">{usuario.username}</span>
          </div>
          {usuario.email && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">E-mail:</span>
              <span className="text-foreground">{usuario.email}</span>
            </div>
          )}
        </div>

        {/* Perfil Operacional */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-foreground">
            Perfil de Permissões
          </label>
          <select
            value={grupoId}
            onChange={(e) => setGrupoId(e.target.value)}
            className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-colors"
          >
            <option value="">Sem perfil atribuído</option>
            {perfis.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nome} ({p.interno})
              </option>
            ))}
          </select>
        </div>

        {/* Status Ativo */}
        <div className="space-y-3 pt-2 border-t border-border">
          <label className="flex items-start gap-2.5 p-2.5 rounded-lg border border-border bg-card cursor-pointer hover:bg-muted/40 transition-colors">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="mt-0.5 rounded border-gray-300 text-primary focus:ring-primary h-4 w-4"
            />
            <div className="space-y-0.5 text-xs">
              <span className="font-semibold text-foreground">Conta Ativa</span>
              <p className="text-muted-foreground">
                Se desativado, o colaborador não conseguirá fazer login nem acessar nenhuma rota da aplicação.
              </p>
            </div>
          </label>

          <label className="flex items-start gap-2.5 p-2.5 rounded-lg border border-border bg-card cursor-pointer hover:bg-muted/40 transition-colors">
            <input
              type="checkbox"
              checked={isSuperuser}
              onChange={(e) => setIsSuperuser(e.target.checked)}
              className="mt-0.5 rounded border-gray-300 text-primary focus:ring-primary h-4 w-4"
            />
            <div className="space-y-0.5 text-xs">
              <span className="font-semibold text-foreground flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-primary" />
                Acesso de Superadministrador
              </span>
              <p className="text-muted-foreground">
                Concede autoridade máxima, permitindo criar outros administradores e excluir fechamentos e cadastros.
              </p>
            </div>
          </label>
        </div>

        {/* Ações */}
        <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={atualizarMutation.isPending}
          >
            Cancelar
          </Button>
          <Button type="submit" disabled={atualizarMutation.isPending}>
            {atualizarMutation.isPending ? 'Salvando...' : 'Salvar Permissões'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
