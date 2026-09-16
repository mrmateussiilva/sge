import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AppLayout } from '@/components/layout/AppLayout'
import { DashboardPage } from '@/pages/DashboardPage'
import { ProdutosPage } from '@/pages/ProdutosPage'
import { ProdutoDetalhePage } from '@/pages/ProdutoDetalhePage'
import { MovimentacoesPage } from '@/pages/MovimentacoesPage'
import { OrdensPage } from '@/pages/OrdensPage'
import { OrdemDetalhePage } from '@/pages/OrdemDetalhePage'
import { FornecedoresPage } from '@/pages/FornecedoresPage'
import { CategoriasPage } from '@/pages/CategoriasPage'
import { RelatoriosPage } from '@/pages/RelatoriosPage'
import { FechamentosPage } from '@/pages/FechamentosPage'
import { FechamentoDetalhePage } from '@/pages/FechamentoDetalhePage'
import { LogsPage } from '@/pages/LogsPage'
import { UsuariosPage } from '@/pages/UsuariosPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

const basename = typeof window !== 'undefined' && window.location.pathname.startsWith('/app') ? '/app' : '/'

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename={basename}>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="produtos" element={<ProdutosPage />} />
            <Route path="produtos/:id" element={<ProdutoDetalhePage />} />
            <Route path="movimentacoes" element={<MovimentacoesPage />} />
            <Route path="ordens" element={<OrdensPage />} />
            <Route path="ordens/:id" element={<OrdemDetalhePage />} />
            <Route path="fornecedores" element={<FornecedoresPage />} />
            <Route path="categorias" element={<CategoriasPage />} />
            <Route path="relatorios" element={<RelatoriosPage />} />
            <Route path="fechamentos" element={<FechamentosPage />} />
            <Route path="fechamentos/:id" element={<FechamentoDetalhePage />} />
            <Route path="logs" element={<LogsPage />} />
            <Route path="usuarios" element={<UsuariosPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
