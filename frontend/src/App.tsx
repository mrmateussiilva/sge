import { lazy, Suspense } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AppLayout } from '@/components/layout/AppLayout'

const DashboardPage = lazy(() => import('@/pages/DashboardPage').then(m => ({ default: m.DashboardPage })))
const ProdutosPage = lazy(() => import('@/pages/ProdutosPage').then(m => ({ default: m.ProdutosPage })))
const ProdutoDetalhePage = lazy(() => import('@/pages/ProdutoDetalhePage').then(m => ({ default: m.ProdutoDetalhePage })))
const MovimentacoesPage = lazy(() => import('@/pages/MovimentacoesPage').then(m => ({ default: m.MovimentacoesPage })))
const OrdensPage = lazy(() => import('@/pages/OrdensPage').then(m => ({ default: m.OrdensPage })))
const OrdemDetalhePage = lazy(() => import('@/pages/OrdemDetalhePage').then(m => ({ default: m.OrdemDetalhePage })))
const FornecedoresPage = lazy(() => import('@/pages/FornecedoresPage').then(m => ({ default: m.FornecedoresPage })))
const CategoriasPage = lazy(() => import('@/pages/CategoriasPage').then(m => ({ default: m.CategoriasPage })))
const RelatoriosPage = lazy(() => import('@/pages/RelatoriosPage').then(m => ({ default: m.RelatoriosPage })))
const FechamentosPage = lazy(() => import('@/pages/FechamentosPage').then(m => ({ default: m.FechamentosPage })))
const FechamentoDetalhePage = lazy(() => import('@/pages/FechamentoDetalhePage').then(m => ({ default: m.FechamentoDetalhePage })))
const LogsPage = lazy(() => import('@/pages/LogsPage').then(m => ({ default: m.LogsPage })))
const UsuariosPage = lazy(() => import('@/pages/UsuariosPage').then(m => ({ default: m.UsuariosPage })))
const NotificacoesPage = lazy(() => import('@/pages/NotificacoesPage').then(m => ({ default: m.NotificacoesPage })))
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage').then(m => ({ default: m.NotFoundPage })))

function PageLoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-[50vh]">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
    </div>
  )
}

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
            <Route
              index
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <DashboardPage />
                </Suspense>
              }
            />
            <Route
              path="produtos"
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <ProdutosPage />
                </Suspense>
              }
            />
            <Route
              path="produtos/:id"
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <ProdutoDetalhePage />
                </Suspense>
              }
            />
            <Route
              path="movimentacoes"
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <MovimentacoesPage />
                </Suspense>
              }
            />
            <Route
              path="ordens"
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <OrdensPage />
                </Suspense>
              }
            />
            <Route
              path="ordens/:id"
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <OrdemDetalhePage />
                </Suspense>
              }
            />
            <Route
              path="fornecedores"
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <FornecedoresPage />
                </Suspense>
              }
            />
            <Route
              path="categorias"
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <CategoriasPage />
                </Suspense>
              }
            />
            <Route
              path="relatorios"
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <RelatoriosPage />
                </Suspense>
              }
            />
            <Route
              path="fechamentos"
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <FechamentosPage />
                </Suspense>
              }
            />
            <Route
              path="fechamentos/:id"
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <FechamentoDetalhePage />
                </Suspense>
              }
            />
            <Route
              path="logs"
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <LogsPage />
                </Suspense>
              }
            />
            <Route
              path="usuarios"
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <UsuariosPage />
                </Suspense>
              }
            />
            <Route
              path="notificacoes"
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <NotificacoesPage />
                </Suspense>
              }
            />
            <Route
              path="*"
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <NotFoundPage />
                </Suspense>
              }
            />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
