import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Search,
  LayoutDashboard,
  Package,
  ArrowLeftRight,
  ShoppingCart,
  Truck,
  FolderTree,
  CalendarCheck,
  FileBarChart,
  History,
  Users,
  Sun,
  Moon,
  Eye,
  EyeOff,
  CornerDownLeft,
  Loader2,
  Boxes,
  X,
} from 'lucide-react'
import { api } from '@/api/client'
import { usePreferences } from '@/hooks/usePreferences'
import { useDebounce } from '@/hooks/useDebounce'
import type { ProdutosResponse } from '@/types'

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

interface CommandItem {
  id: string
  title: string
  subtitle?: string
  icon: any
  category: 'Ações' | 'Navegação' | 'Produtos'
  action: () => void
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const navigate = useNavigate()
  const { isDark, toggleTheme, ocultarValores, toggleOcultarValores } = usePreferences()
  const [busca, setBusca] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const debouncedBusca = useDebounce(busca, 250)

  // Foco no input ao abrir
  useEffect(() => {
    if (isOpen) {
      setBusca('')
      setSelectedIndex(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  // Busca rápida de produtos pela API quando o usuário digita
  const { data: produtosData, isLoading: isLoadingProdutos } = useQuery({
    queryKey: ['command-palette-produtos', debouncedBusca],
    queryFn: () => {
      if (!debouncedBusca.trim() || debouncedBusca.trim().length < 2) {
        return Promise.resolve({ ok: true, itens: [] } as any)
      }
      return api.get<ProdutosResponse>(
        `/api/v1/produtos/?busca=${encodeURIComponent(debouncedBusca.trim())}&page_size=6`
      )
    },
    enabled: isOpen && debouncedBusca.trim().length >= 2,
  })

  // Lista estática de páginas e atalhos rápidos
  const navItems: CommandItem[] = [
    {
      id: 'nav-dashboard',
      title: 'Dashboard Geral',
      subtitle: 'Métricas, KPIs e saldos críticos',
      icon: LayoutDashboard,
      category: 'Navegação',
      action: () => {
        navigate('/')
        onClose()
      },
    },
    {
      id: 'nav-produtos',
      title: 'Catálogo de Produtos',
      subtitle: 'Listagem de insumos e tecidos',
      icon: Package,
      category: 'Navegação',
      action: () => {
        navigate('/produtos')
        onClose()
      },
    },
    {
      id: 'nav-movimentacoes',
      title: 'Registro de Movimentações',
      subtitle: 'Entradas e saídas de estoque',
      icon: ArrowLeftRight,
      category: 'Navegação',
      action: () => {
        navigate('/movimentacoes')
        onClose()
      },
    },
    {
      id: 'nav-ordens',
      title: 'Ordens de Compra',
      subtitle: 'Pedidos de reposição a fornecedores',
      icon: ShoppingCart,
      category: 'Navegação',
      action: () => {
        navigate('/ordens')
        onClose()
      },
    },
    {
      id: 'nav-fornecedores',
      title: 'Gestão de Fornecedores',
      subtitle: 'Cadastro de contatos e parceiros',
      icon: Truck,
      category: 'Navegação',
      action: () => {
        navigate('/fornecedores')
        onClose()
      },
    },
    {
      id: 'nav-categorias',
      title: 'Categorias de Produtos',
      subtitle: 'Organização de grupos e tipos',
      icon: FolderTree,
      category: 'Navegação',
      action: () => {
        navigate('/categorias')
        onClose()
      },
    },
    {
      id: 'nav-fechamentos',
      title: 'Fechamentos Mensais',
      subtitle: 'Histórico contábil e snapshots de saldo',
      icon: CalendarCheck,
      category: 'Navegação',
      action: () => {
        navigate('/fechamentos')
        onClose()
      },
    },
    {
      id: 'nav-relatorios',
      title: 'Relatórios do Estoque',
      subtitle: 'Consolidado do período e movimentações',
      icon: FileBarChart,
      category: 'Navegação',
      action: () => {
        navigate('/relatorios')
        onClose()
      },
    },
    {
      id: 'nav-logs',
      title: 'Trilha de Auditoria',
      subtitle: 'Registro de segurança e histórico de ações',
      icon: History,
      category: 'Navegação',
      action: () => {
        navigate('/logs')
        onClose()
      },
    },
    {
      id: 'nav-usuarios',
      title: 'Usuários & Permissões',
      subtitle: 'Controle de contas e acesso',
      icon: Users,
      category: 'Navegação',
      action: () => {
        navigate('/usuarios')
        onClose()
      },
    },
  ]

  const actionItems: CommandItem[] = [
    {
      id: 'act-toggle-theme',
      title: isDark ? 'Ativar Tema Claro' : 'Ativar Tema Escuro',
      subtitle: 'Alternar tema visual da interface',
      icon: isDark ? Sun : Moon,
      category: 'Ações',
      action: () => {
        toggleTheme()
        onClose()
      },
    },
    {
      id: 'act-toggle-valores',
      title: ocultarValores ? 'Revelar Preços e Totais' : 'Ocultar Valores Sensíveis',
      subtitle: 'Privacidade de custos em tela',
      icon: ocultarValores ? Eye : EyeOff,
      category: 'Ações',
      action: () => {
        toggleOcultarValores()
        onClose()
      },
    },
    {
      id: 'act-novo-produto',
      title: 'Cadastrar Novo Insumo',
      subtitle: 'Ir para o formulário de produtos',
      icon: Package,
      category: 'Ações',
      action: () => {
        navigate('/produtos')
        onClose()
      },
    },
    {
      id: 'act-nova-mov',
      title: 'Registrar Nova Movimentação',
      subtitle: 'Dar entrada ou saída física de estoque',
      icon: ArrowLeftRight,
      category: 'Ações',
      action: () => {
        navigate('/movimentacoes')
        onClose()
      },
    },
  ]

  // Converte produtos pesquisados em items
  const produtoItems: CommandItem[] = (produtosData?.itens || []).map((p: any) => ({
    id: `prod-${p.id}`,
    title: p.descricao,
    subtitle: `${p.tipo_produto_display} • Saldo: ${p.quantidade_formatada} • ${p.fornecedor || 'Sem fornecedor'}`,
    icon: Boxes,
    category: 'Produtos',
    action: () => {
      navigate(`/produtos/${p.id}`)
      onClose()
    },
  }))

  // Filtra ações e navegação com o termo
  const termoLower = busca.trim().toLowerCase()
  const filteredNav = navItems.filter(
    (item) =>
      item.title.toLowerCase().includes(termoLower) ||
      (item.subtitle && item.subtitle.toLowerCase().includes(termoLower))
  )
  const filteredActions = actionItems.filter(
    (item) =>
      item.title.toLowerCase().includes(termoLower) ||
      (item.subtitle && item.subtitle.toLowerCase().includes(termoLower))
  )

  const allFilteredItems: CommandItem[] = [
    ...produtoItems,
    ...filteredActions,
    ...filteredNav,
  ]

  // Ajusta index se mudar tamanho
  useEffect(() => {
    setSelectedIndex(0)
  }, [busca, produtoItems.length])

  // Navegação por teclado
  useEffect(() => {
    if (!isOpen) return

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((prev) =>
          prev < allFilteredItems.length - 1 ? prev + 1 : 0
        )
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((prev) =>
          prev > 0 ? prev - 1 : allFilteredItems.length - 1
        )
      } else if (e.key === 'Enter') {
        e.preventDefault()
        if (allFilteredItems[selectedIndex]) {
          allFilteredItems[selectedIndex].action()
        }
      } else if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, selectedIndex, allFilteredItems, onClose])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 px-4 bg-black/60 backdrop-blur-xs animate-in fade-in-0 duration-150"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl bg-card border border-border rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh] animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Input Header */}
        <div className="flex items-center px-4 border-b border-border bg-muted/20">
          <Search className="w-5 h-5 text-muted-foreground shrink-0" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Digite para buscar insumos, telas ou executar ações..."
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            className="w-full px-3 py-3.5 bg-transparent text-sm focus:outline-none placeholder:text-muted-foreground text-foreground"
          />
          {busca && (
            <button
              onClick={() => setBusca('')}
              className="p-1 text-muted-foreground hover:text-foreground rounded-md mr-1"
              title="Limpar busca"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <kbd className="hidden sm:inline-flex items-center px-2 py-0.5 text-[10px] font-semibold text-muted-foreground bg-muted border border-border rounded">
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div ref={listRef} className="overflow-y-auto p-2 space-y-4 max-h-[60vh]">
          {isLoadingProdutos && busca.trim().length >= 2 && (
            <div className="p-4 flex items-center justify-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin text-primary" />
              <span>Buscando produtos no estoque...</span>
            </div>
          )}

          {allFilteredItems.length === 0 ? (
            <div className="p-8 text-center space-y-1">
              <Search className="w-8 h-8 text-muted-foreground/60 mx-auto" />
              <p className="text-sm font-medium text-foreground">Nenhum resultado encontrado</p>
              <p className="text-xs text-muted-foreground">
                Tente buscar pelo nome de um produto, código ou tela do sistema.
              </p>
            </div>
          ) : (
            <>
              {/* Seção Produtos Encontrados */}
              {produtoItems.length > 0 && (
                <div>
                  <div className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-primary">
                    Produtos Encontrados
                  </div>
                  <div className="space-y-0.5">
                    {produtoItems.map((item) => {
                      const itemIndex = allFilteredItems.findIndex((i) => i.id === item.id)
                      const isSelected = itemIndex === selectedIndex
                      const Icon = item.icon
                      return (
                        <div
                          key={item.id}
                          onClick={item.action}
                          onMouseEnter={() => setSelectedIndex(itemIndex)}
                          className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-primary text-primary-foreground'
                              : 'hover:bg-muted text-foreground'
                          }`}
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <div
                              className={`p-1.5 rounded-md ${
                                isSelected ? 'bg-primary-foreground/20' : 'bg-muted'
                              }`}
                            >
                              <Icon className="w-4 h-4" />
                            </div>
                            <div className="min-w-0">
                              <p className="text-sm font-semibold truncate leading-none">
                                {item.title}
                              </p>
                              {item.subtitle && (
                                <p
                                  className={`text-xs mt-1 truncate ${
                                    isSelected
                                      ? 'text-primary-foreground/80'
                                      : 'text-muted-foreground'
                                  }`}
                                >
                                  {item.subtitle}
                                </p>
                              )}
                            </div>
                          </div>
                          {isSelected && (
                            <CornerDownLeft className="w-4 h-4 shrink-0 opacity-80" />
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Seção Ações Rápidas */}
              {filteredActions.length > 0 && (
                <div>
                  <div className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Ações Rápidas
                  </div>
                  <div className="space-y-0.5">
                    {filteredActions.map((item) => {
                      const itemIndex = allFilteredItems.findIndex((i) => i.id === item.id)
                      const isSelected = itemIndex === selectedIndex
                      const Icon = item.icon
                      return (
                        <div
                          key={item.id}
                          onClick={item.action}
                          onMouseEnter={() => setSelectedIndex(itemIndex)}
                          className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-primary text-primary-foreground'
                              : 'hover:bg-muted text-foreground'
                          }`}
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <div
                              className={`p-1.5 rounded-md ${
                                isSelected ? 'bg-primary-foreground/20' : 'bg-muted'
                              }`}
                            >
                              <Icon className="w-4 h-4" />
                            </div>
                            <div className="min-w-0">
                              <p className="text-sm font-medium truncate leading-none">
                                {item.title}
                              </p>
                              {item.subtitle && (
                                <p
                                  className={`text-xs mt-1 truncate ${
                                    isSelected
                                      ? 'text-primary-foreground/80'
                                      : 'text-muted-foreground'
                                  }`}
                                >
                                  {item.subtitle}
                                </p>
                              )}
                            </div>
                          </div>
                          {isSelected && (
                            <CornerDownLeft className="w-4 h-4 shrink-0 opacity-80" />
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Seção Navegação */}
              {filteredNav.length > 0 && (
                <div>
                  <div className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Navegação
                  </div>
                  <div className="space-y-0.5">
                    {filteredNav.map((item) => {
                      const itemIndex = allFilteredItems.findIndex((i) => i.id === item.id)
                      const isSelected = itemIndex === selectedIndex
                      const Icon = item.icon
                      return (
                        <div
                          key={item.id}
                          onClick={item.action}
                          onMouseEnter={() => setSelectedIndex(itemIndex)}
                          className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-primary text-primary-foreground'
                              : 'hover:bg-muted text-foreground'
                          }`}
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <div
                              className={`p-1.5 rounded-md ${
                                isSelected ? 'bg-primary-foreground/20' : 'bg-muted'
                              }`}
                            >
                              <Icon className="w-4 h-4" />
                            </div>
                            <div className="min-w-0">
                              <p className="text-sm font-medium truncate leading-none">
                                {item.title}
                              </p>
                              {item.subtitle && (
                                <p
                                  className={`text-xs mt-1 truncate ${
                                    isSelected
                                      ? 'text-primary-foreground/80'
                                      : 'text-muted-foreground'
                                  }`}
                                >
                                  {item.subtitle}
                                </p>
                              )}
                            </div>
                          </div>
                          {isSelected && (
                            <CornerDownLeft className="w-4 h-4 shrink-0 opacity-80" />
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer com atalhos */}
        <div className="px-4 py-2 bg-muted/40 border-t border-border flex items-center justify-between text-[11px] text-muted-foreground">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-card border border-border rounded font-semibold text-[10px]">
                ↑
              </kbd>
              <kbd className="px-1.5 py-0.5 bg-card border border-border rounded font-semibold text-[10px]">
                ↓
              </kbd>
              <span>Navegar</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-card border border-border rounded font-semibold text-[10px]">
                ↵
              </kbd>
              <span>Selecionar</span>
            </span>
          </div>
          <div>
            <span>SGE Busca Rápida</span>
          </div>
        </div>
      </div>
    </div>
  )
}
