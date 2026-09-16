import { useLocation } from 'react-router-dom'
import {
  Menu,
  Sun,
  Moon,
  Eye,
  EyeOff,
  LogOut,
  Bell,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/useAuth'
import { usePreferences } from '@/hooks/usePreferences'
import { api } from '@/api/client'

interface NavbarProps {
  onToggleMobileMenu: () => void
}

const ROUTE_TITLES: Record<string, string> = {
  '/': 'Dashboard de Controle',
  '/produtos': 'Catálogo de Produtos',
  '/movimentacoes': 'Registro de Movimentações',
  '/ordens': 'Ordens de Compra',
  '/fornecedores': 'Gestão de Fornecedores',
  '/categorias': 'Categorias de Produtos',
  '/relatorios': 'Relatório Mensal',
  '/fechamentos': 'Fechamento de Estoque',
  '/logs': 'Auditoria de Ações',
  '/usuarios': 'Usuários & Permissões',
}

export function Navbar({ onToggleMobileMenu }: NavbarProps) {
  const location = useLocation()
  const { user, alertas } = useAuth()
  const { isDark, toggleTheme, ocultarValores, toggleOcultarValores } = usePreferences()

  const currentTitle = ROUTE_TITLES[location.pathname] || 'SGE Estoque'

  async function handleLogout() {
    try {
      await api.post('/api/v1/auth/logout/')
    } catch {
      // Ignora erro
    } finally {
      window.location.href = '/accounts/login/'
    }
  }

  return (
    <header className="h-16 px-4 md:px-6 bg-card border-b border-border flex items-center justify-between sticky top-0 z-30 shadow-xs">
      {/* Lado Esquerdo: Mobile Trigger & Título */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={onToggleMobileMenu}
          aria-label="Abrir menu"
        >
          <Menu className="w-5 h-5" />
        </Button>

        <div>
          <h2 className="text-base font-semibold text-foreground leading-none">
            {currentTitle}
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5 hidden sm:block">
            Ambiente Operacional
          </p>
        </div>
      </div>

      {/* Lado Direito: Ações Rápidas, Tema e Usuário */}
      <div className="flex items-center gap-1.5 md:gap-2">
        {/* Toggle Ocultar Valores */}
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleOcultarValores}
          className="text-xs gap-1.5 hidden sm:flex text-muted-foreground hover:text-foreground"
          title={ocultarValores ? 'Revelar preços e métricas' : 'Ocultar valores sensíveis'}
        >
          {ocultarValores ? (
            <>
              <EyeOff className="w-4 h-4 text-amber-500" />
              <span>Valores Ocultos</span>
            </>
          ) : (
            <>
              <Eye className="w-4 h-4" />
              <span>Ocultar Valores</span>
            </>
          )}
        </Button>

        {/* Toggle Tema */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          aria-label="Alternar tema"
          title={isDark ? 'Mudar para tema claro' : 'Mudar para tema escuro'}
        >
          {isDark ? (
            <Sun className="w-4 h-4 text-amber-400" />
          ) : (
            <Moon className="w-4 h-4 text-muted-foreground" />
          )}
        </Button>

        {/* Alerta de Estoque Crítico */}
        {Boolean(alertas?.estoque_baixo || alertas?.estoque_zerado) && (
          <div className="relative">
            <Button
              variant="ghost"
              size="icon"
              title={`${(alertas?.estoque_baixo || 0) + (alertas?.estoque_zerado || 0)} itens com estoque em atenção`}
            >
              <Bell className="w-4 h-4 text-amber-500" />
            </Button>
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
          </div>
        )}

        {/* Divisor */}
        <div className="w-px h-6 bg-border mx-1" />

        {/* Usuário e Logout */}
        <div className="flex items-center gap-2">
          <div className="text-right hidden lg:block">
            <p className="text-xs font-medium leading-none">{user?.username}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">{user?.perfil}</p>
          </div>

          <Button
            variant="ghost"
            size="icon"
            onClick={handleLogout}
            title="Sair do sistema"
            className="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
          >
            <LogOut className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </header>
  )
}
