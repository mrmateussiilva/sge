import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { HelpCircle } from 'lucide-react'

export function NotFoundPage() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center p-4">
      <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4 text-muted-foreground">
        <HelpCircle className="w-6 h-6" />
      </div>
      <h1 className="text-2xl font-bold mb-2">Página não encontrada</h1>
      <p className="text-sm text-muted-foreground max-w-sm mb-6">
        O endereço solicitado não existe ou foi movido para outra rota do sistema.
      </p>
      <Button asChild>
        <Link to="/">Voltar ao Dashboard</Link>
      </Button>
    </div>
  )
}
