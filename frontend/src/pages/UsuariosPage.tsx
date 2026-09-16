import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus, ShieldCheck, UserCheck, Search, Users, CheckCircle2, XCircle } from 'lucide-react'
import { api } from '@/api/client'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { UsuarioCriarModal } from '@/components/usuarios/UsuarioCriarModal'
import { UsuarioPerfilModal } from '@/components/usuarios/UsuarioPerfilModal'

export function UsuariosPage() {
  const [busca, setBusca] = useState('')
  const [modalCriarAberto, setModalCriarAberto] = useState(false)
  const [usuarioSelecionado, setUsuarioSelecionado] = useState<any | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['usuarios'],
    queryFn: () => api.get<any>('/api/v1/usuarios/'),
  })

  const usuarios = data?.usuarios || []
  const perfis = data?.perfis || []

  const usuariosFiltrados = usuarios.filter((u: any) => {
    if (!busca.trim()) return true
    const termo = busca.toLowerCase()
    return (
      u.username.toLowerCase().includes(termo) ||
      (u.email && u.email.toLowerCase().includes(termo)) ||
      (u.perfil && u.perfil.toLowerCase().includes(termo))
    )
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Controle de Acessos & Usuários</h1>
          <p className="text-sm text-muted-foreground">
            Gerenciamento centralizado de contas, perfis operacionais e permissões administrativas.
          </p>
        </div>
        <Button
          onClick={() => setModalCriarAberto(true)}
          className="gap-1.5 self-start sm:self-auto shadow-xs"
        >
          <Plus className="w-4 h-4" />
          <span>Cadastrar Usuário</span>
        </Button>
      </div>

      {/* Busca */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por nome, login, e-mail..."
            className="pl-9"
          />
        </div>
        <div className="text-xs text-muted-foreground self-end sm:self-auto">
          Total: <span className="font-semibold text-foreground">{usuariosFiltrados.length}</span> usuário(s)
        </div>
      </div>

      {/* Tabela de Usuários */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-12 text-center text-sm text-muted-foreground">
              Carregando lista de usuários...
            </div>
          ) : usuariosFiltrados.length === 0 ? (
            <div className="p-12 text-center space-y-2">
              <Users className="w-10 h-10 text-muted-foreground/60 mx-auto" />
              <p className="font-semibold text-sm text-foreground">
                Nenhum usuário encontrado
              </p>
              <p className="text-xs text-muted-foreground">
                Tente ajustar os filtros ou cadastre um novo usuário.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs uppercase bg-muted/50 text-muted-foreground border-b border-border">
                  <tr>
                    <th className="px-4 py-3.5 font-semibold">Login / Usuário</th>
                    <th className="px-4 py-3.5 font-semibold">E-mail</th>
                    <th className="px-4 py-3.5 font-semibold">Perfil de Acesso</th>
                    <th className="px-4 py-3.5 font-semibold text-center">Status</th>
                    <th className="px-4 py-3.5 font-semibold text-center">Nível Master</th>
                    <th className="px-4 py-3.5 font-semibold text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {usuariosFiltrados.map((u: any) => (
                    <tr key={u.id} className="hover:bg-muted/40 transition-colors">
                      <td className="px-4 py-3.5 font-semibold text-foreground">
                        {u.username}
                      </td>
                      <td className="px-4 py-3.5 text-muted-foreground text-xs">
                        {u.email || '—'}
                      </td>
                      <td className="px-4 py-3.5">
                        <Badge
                          variant={u.perfil === 'Administrador' ? 'default' : 'secondary'}
                          className="font-medium"
                        >
                          {u.perfil}
                        </Badge>
                      </td>
                      <td className="px-4 py-3.5 text-center">
                        {u.is_active ? (
                          <span className="inline-flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Ativo
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground font-medium">
                            <XCircle className="w-3.5 h-3.5" /> Inativo
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-center">
                        {u.is_superuser ? (
                          <span className="inline-flex items-center gap-1 text-xs text-primary font-semibold">
                            <ShieldCheck className="w-3.5 h-3.5" /> Superusuário
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">Padrão</span>
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setUsuarioSelecionado(u)}
                          className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
                        >
                          <UserCheck className="w-3.5 h-3.5" />
                          <span>Gerenciar Acesso</span>
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modais */}
      <UsuarioCriarModal
        isOpen={modalCriarAberto}
        onClose={() => setModalCriarAberto(false)}
        perfis={perfis}
      />

      <UsuarioPerfilModal
        isOpen={Boolean(usuarioSelecionado)}
        onClose={() => setUsuarioSelecionado(null)}
        usuario={usuarioSelecionado}
        perfis={perfis}
      />
    </div>
  )
}
