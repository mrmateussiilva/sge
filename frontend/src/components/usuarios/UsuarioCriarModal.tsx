import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { UserPlus, Shield } from 'lucide-react'
import { api } from '@/api/client'
import { Modal } from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface UsuarioCriarModalProps {
  isOpen: boolean
  onClose: () => void
  perfis: Array<{ id: number; nome: string; interno: string }>
}

export function UsuarioCriarModal({
  isOpen,
  onClose,
  perfis,
}: UsuarioCriarModalProps) {
  const queryClient = useQueryClient()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [grupoId, setGrupoId] = useState<string>('')
  const [isSuperuser, setIsSuperuser] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      setUsername('')
      setPassword('')
      setEmail('')
      setGrupoId(perfis.length > 0 ? String(perfis[0].id) : '')
      setIsSuperuser(false)
      setErro(null)
    }
  }, [isOpen, perfis])

  const criarMutation = useMutation({
    mutationFn: async () => {
      return api.post<{ ok: boolean; id?: number; mensagem?: string; erro?: string }>(
        '/api/v1/usuarios/criar/',
        {
          username: username.trim(),
          password,
          email: email.trim(),
          grupo_id: grupoId ? Number(grupoId) : null,
          is_superuser: isSuperuser,
        }
      )
    },
    onSuccess: (res) => {
      if (res.ok) {
        toast.success(res.mensagem || 'Usuário criado com sucesso!')
        queryClient.invalidateQueries({ queryKey: ['usuarios'] })
        onClose()
      } else {
        setErro(res.erro || 'Erro ao criar usuário.')
        toast.error(res.erro || 'Erro ao criar usuário.')
      }
    },
    onError: (err: any) => {
      const msg = err.response?.data?.erro || err.message || 'Erro inesperado ao criar usuário.'
      setErro(msg)
      toast.error(msg)
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!username.trim()) {
      setErro('O nome de usuário é obrigatório.')
      return
    }
    if (!password) {
      setErro('A senha é obrigatória.')
      return
    }
    setErro(null)
    criarMutation.mutate()
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <UserPlus className="w-5 h-5 text-primary" />
          <span>Cadastrar Novo Usuário</span>
        </div>
      }
      description="Crie credenciais de acesso para colaboradores e atribua as permissões operacionais cabíveis."
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {erro && (
          <div className="p-3 text-xs rounded-lg bg-destructive/10 text-destructive border border-destructive/20 font-medium">
            {erro}
          </div>
        )}

        {/* Login de Acesso */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-foreground">
            Nome de Usuário (Login) <span className="text-destructive">*</span>
          </label>
          <Input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Ex: joao.silva"
            required
            autoFocus
          />
        </div>

        {/* Senha */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-foreground">
            Senha Inicial <span className="text-destructive">*</span>
          </label>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
          />
        </div>

        {/* E-mail */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-foreground">
            E-mail Institucional <span className="text-xs text-muted-foreground font-normal">(Opcional)</span>
          </label>
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="colaborador@empresa.com"
          />
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

        {/* Superusuário Checkbox */}
        <div className="pt-2 border-t border-border">
          <label className="flex items-start gap-2.5 p-2.5 rounded-lg border border-border bg-muted/30 cursor-pointer hover:bg-muted/50 transition-colors">
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
                Permite gerenciar outros usuários, configurar integrações e excluir registros protegidos.
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
            disabled={criarMutation.isPending}
          >
            Cancelar
          </Button>
          <Button type="submit" disabled={criarMutation.isPending}>
            {criarMutation.isPending ? 'Criando...' : 'Cadastrar Usuário'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
