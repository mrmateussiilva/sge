import { useState } from 'react'
import { Bell, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { Modal } from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { api } from '@/api/client'

interface NotificacaoTesteModalProps {
  isOpen: boolean
  onClose: () => void
}

export function NotificacaoTesteModal({ isOpen, onClose }: NotificacaoTesteModalProps) {
  const [audience, setAudience] = useState('admin')
  const [mensagem, setMensagem] = useState('Este é um teste de notificação enviado pelo SGE!')
  const [isLoading, setIsLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!audience.trim() || !mensagem.trim()) {
      toast.error('Preencha a audiência e a mensagem.')
      return
    }

    setIsLoading(true)
    try {
      const response = await api.post<{ ok: boolean; mensagem?: string; erro?: string }>('/api/v1/notificacoes/teste/', {
        audience,
        mensagem
      })

      if (response.ok) {
        toast.success(response.mensagem || 'Notificação enviada com sucesso!')
        onClose()
      } else {
        toast.error(response.erro || 'Falha ao enviar notificação.')
      }
    } catch (error: any) {
      toast.error('Erro de comunicação com o servidor.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Testar Notificação (Webhook)"
      description="Envie um evento de teste para o n8n e verifique se chega no WhatsApp."
      maxWidth="sm"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Audiência (Destino)</label>
          <input
            type="text"
            className="w-full flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
            placeholder="Ex: admin"
            required
          />
          <p className="text-xs text-muted-foreground">O n8n usará isso para rotear a mensagem.</p>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Mensagem</label>
          <textarea
            className="w-full flex min-h-[80px] rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            value={mensagem}
            onChange={(e) => setMensagem(e.target.value)}
            placeholder="Digite a mensagem de teste..."
            required
          />
        </div>

        <div className="flex justify-end gap-2 pt-4">
          <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
            Cancelar
          </Button>
          <Button type="submit" disabled={isLoading} className="gap-2">
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bell className="w-4 h-4" />}
            Enviar Teste
          </Button>
        </div>
      </form>
    </Modal>
  )
}
