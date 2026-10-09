import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { KeyRound, ShieldCheck, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react'
import { api } from '@/api/client'
import { Modal } from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { OmieConfigResponse } from '@/types'

interface OmieConfigModalProps {
  isOpen: boolean
  onClose: () => void
}

export function OmieConfigModal({ isOpen, onClose }: OmieConfigModalProps) {
  const queryClient = useQueryClient()
  const [appKey, setAppKey] = useState('')
  const [appSecret, setAppSecret] = useState('')
  const [erro, setErro] = useState<string | null>(null)

  const { data: configData, isLoading: isLoadingConfig } = useQuery({
    queryKey: ['omie-config'],
    queryFn: () => api.get<OmieConfigResponse>('/api/v1/omie/configuracao/'),
    enabled: isOpen,
  })

  useEffect(() => {
    if (isOpen) {
      setAppKey('')
      setAppSecret('')
      setErro(null)
    }
  }, [isOpen])

  const salvarMutation = useMutation({
    mutationFn: async () => {
      if (!appKey.trim() && !configData?.configurado) {
        throw new Error('Informe o App Key da Omie.')
      }
      if (!appSecret.trim() && !configData?.configurado) {
        throw new Error('Informe o App Secret da Omie.')
      }
      return api.post('/api/v1/omie/configuracao/salvar/', {
        app_key: appKey.trim(),
        app_secret: appSecret.trim(),
      })
    },
    onSuccess: () => {
      toast.success('Credenciais da Omie atualizadas com sucesso!')
      queryClient.invalidateQueries({ queryKey: ['omie-config'] })
      queryClient.invalidateQueries({ queryKey: ['omie-notas'] })
      onClose()
    },
    onError: (err: any) => {
      const msg = err?.message || 'Falha ao salvar credenciais da Omie.'
      setErro(msg)
      toast.error(msg)
    },
  })

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Configuração de Integração Omie"
      description="Credenciais de acesso à API Omie para leitura automática de notas de fornecedores."
      maxWidth="md"
    >
      <div className="space-y-5 py-2">
        {isLoadingConfig ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
          </div>
        ) : (
          <>
            {/* Status atual */}
            <div className="p-3.5 rounded-xl border border-border/80 bg-muted/30 flex items-start gap-3">
              {configData?.configurado ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
              )}
              <div className="text-xs space-y-1">
                <div className="font-semibold text-foreground flex items-center gap-2">
                  <span>Status:</span>
                  {configData?.configurado ? (
                    <span className="text-emerald-500 font-medium">Conectado à Omie</span>
                  ) : (
                    <span className="text-amber-500 font-medium">Credenciais pendentes</span>
                  )}
                </div>
                {configData?.app_key_mascarada && (
                  <p className="text-muted-foreground">
                    Chave ativa: <code className="bg-background px-1.5 py-0.5 rounded text-foreground font-mono">{configData.app_key_mascarada}</code>
                  </p>
                )}
                {configData?.atualizado_em && (
                  <p className="text-muted-foreground">
                    Última sincronização: {configData.atualizado_em}
                  </p>
                )}
                {configData?.cnpj_proprio && (
                  <p className="text-muted-foreground">
                    CNPJ da empresa (filtro): <code className="bg-background px-1.5 py-0.5 rounded font-mono">{configData.cnpj_proprio}</code>
                  </p>
                )}
              </div>
            </div>

            {erro && (
              <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-xs text-destructive">
                {erro}
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1.5">
                  Omie App Key
                </label>
                <div className="relative">
                  <Input
                    type="text"
                    placeholder={configData?.configurado ? 'Manter chave atual ou digitar nova' : 'Ex: 3852833480496'}
                    value={appKey}
                    onChange={(e) => setAppKey(e.target.value)}
                    className="font-mono text-sm"
                  />
                  <KeyRound className="w-4 h-4 absolute right-3 top-3 text-muted-foreground pointer-events-none" />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1.5">
                  Omie App Secret
                </label>
                <div className="relative">
                  <Input
                    type="password"
                    placeholder={configData?.configurado ? '••••••••••••••••••••••••' : 'Chave secreta de 32 caracteres'}
                    value={appSecret}
                    onChange={(e) => setAppSecret(e.target.value)}
                    className="font-mono text-sm"
                  />
                  <ShieldCheck className="w-4 h-4 absolute right-3 top-3 text-muted-foreground pointer-events-none" />
                </div>
                <p className="text-[11px] text-muted-foreground mt-1.5">
                  As credenciais são armazenadas com criptografia simétrica no banco de dados.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
              <Button variant="outline" onClick={onClose} disabled={salvarMutation.isPending}>
                Cancelar
              </Button>
              <Button
                onClick={() => salvarMutation.mutate()}
                disabled={salvarMutation.isPending}
              >
                {salvarMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Salvando...
                  </>
                ) : (
                  'Salvar Credenciais'
                )}
              </Button>
            </div>
          </>
        )}
      </div>
    </Modal>
  )
}
