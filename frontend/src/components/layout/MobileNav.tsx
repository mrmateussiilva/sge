import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Boxes,
  ArrowLeftRight,
  FileSpreadsheet,
  Menu,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface MobileNavProps {
  onOpenMenu: () => void
}

export function MobileNav({ onOpenMenu }: MobileNavProps) {
  const items = [
    { to: '/', label: 'Início', icon: LayoutDashboard },
    { to: '/produtos', label: 'Produtos', icon: Boxes },
    { to: '/movimentacoes', label: 'Mover', icon: ArrowLeftRight },
    { to: '/ordens', label: 'Ordens', icon: FileSpreadsheet },
  ]

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-card/95 backdrop-blur-md border-t border-border z-40 flex items-center justify-around px-2 shadow-lg">
      {items.map((item) => {
        const Icon = item.icon
        return (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                'flex flex-col items-center justify-center w-14 h-14 rounded-xl transition-all',
                isActive
                  ? 'text-primary font-semibold'
                  : 'text-muted-foreground hover:text-foreground'
              )
            }
          >
            {({ isActive }) => (
              <>
                <Icon className={cn('w-5 h-5', isActive && 'stroke-[2.5] scale-110')} />
                <span className="text-[10px] mt-1 tracking-tight">{item.label}</span>
              </>
            )}
          </NavLink>
        )}
      )}

      <button
        onClick={onOpenMenu}
        className="flex flex-col items-center justify-center w-14 h-14 rounded-xl text-muted-foreground hover:text-foreground transition-all"
        aria-label="Mais opções de menu"
      >
        <Menu className="w-5 h-5" />
        <span className="text-[10px] mt-1 tracking-tight">Mais</span>
      </button>
    </nav>
  )
}
