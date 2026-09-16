import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Boxes,
  ArrowLeftRight,
  FileSpreadsheet,
  Truck,
  Tags,
  BarChart3,
  Lock,
  History,
  Users,
  ExternalLink,
  ShieldCheck,
} from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface SidebarProps {
  className?: string
  onCloseMobile?: () => void
}

export function Sidebar({ className, onCloseMobile }: SidebarProps) {
  const { user, alertas } = useAuth()

  const navItems = [
    {
      label: 'Visão Geral',
      items: [
        { to: '/', label: 'Dashboard', icon: LayoutDashboard },
        {
          to: '/produtos',
          label: 'Produtos',
          icon: Boxes,
          badge: alertas?.estoque_baixo ? String(alertas.estoque_baixo) : undefined,
          badgeVariant: 'warning' as const,
        },
        { to: '/movimentacoes', label: 'Movimentar', icon: ArrowLeftRight },
        {
          to: '/ordens',
          label: 'Ordens de Compra',
          icon: FileSpreadsheet,
          badge: alertas?.ordens_pendentes ? String(alertas.ordens_pendentes) : undefined,
          badgeVariant: 'default' as const,
        },
      ],
    },
    {
      label: 'Cadastros',
      items: [
        { to: '/fornecedores', label: 'Fornecedores', icon: Truck },
        { to: '/categorias', label: 'Categorias', icon: Tags },
      ],
    },
    {
      label: 'Auditoria & Gestão',
      items: [
        { to: '/relatorios', label: 'Relatórios', icon: BarChart3 },
        { to: '/fechamentos', label: 'Fechamentos', icon: Lock },
        { to: '/logs', label: 'Histórico de Logs', icon: History },
        ...(user?.permissoes?.admin
          ? [{ to: '/usuarios', label: 'Usuários & Perfis', icon: Users }]
          : []),
      ],
    },
  ]

  return (
    <aside
      className={cn(
        'flex flex-col h-full bg-card border-r border-border select-none w-64',
        className
      )}
    >
      {/* Brand Header */}
      <div className="flex items-center gap-3 px-6 h-16 border-b border-border">
        <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold text-lg shadow-sm">
          S
        </div>
        <div>
          <h1 className="font-bold text-base leading-tight tracking-tight">SGE Estoque</h1>
          <p className="text-xs text-muted-foreground">Gestão de Insumos</p>
        </div>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        {navItems.map((group, idx) => (
          <div key={idx} className="space-y-1">
            <h2 className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground/80 mb-2">
              {group.label}
            </h2>
            {group.items.map((item) => {
              const Icon = item.icon
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onCloseMobile}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all group',
                      isActive
                        ? 'bg-primary text-primary-foreground shadow-sm font-semibold'
                        : 'text-foreground/80 hover:bg-muted hover:text-foreground'
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <div className="flex items-center gap-3 min-w-0">
                        <Icon
                          className={cn(
                            'w-4 h-4 shrink-0 transition-transform group-hover:scale-110',
                            isActive ? 'text-primary-foreground' : 'text-muted-foreground'
                          )}
                        />
                        <span className="truncate">{item.label}</span>
                      </div>
                      {item.badge && (
                        <Badge
                          variant={isActive ? 'secondary' : item.badgeVariant}
                          className="ml-2 px-1.5 py-0 text-[10px] h-4 leading-none"
                        >
                          {item.badge}
                        </Badge>
                      )}
                    </>
                  )}
                </NavLink>
              )
            })}
          </div>
        ))}

        {/* Django Admin Link */}
        <div className="pt-2 border-t border-border">
          <a
            href="/admin/"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-all"
          >
            <div className="flex items-center gap-3">
              <ShieldCheck className="w-4 h-4 text-muted-foreground" />
              <span>Django Admin</span>
            </div>
            <ExternalLink className="w-3.5 h-3.5 opacity-60" />
          </a>
        </div>
      </div>

      {/* User Footer Profile */}
      {user && (
        <div className="p-3 border-t border-border bg-muted/30">
          <div className="flex items-center gap-3 px-2 py-1.5 rounded-md">
            <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-xs uppercase border border-primary/20">
              {user.username.slice(0, 2)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold truncate leading-none mb-1">
                {user.nome_completo}
              </p>
              <div className="flex items-center gap-1">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <span className="text-[11px] text-muted-foreground truncate">
                  {user.perfil}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </aside>
  )
}
