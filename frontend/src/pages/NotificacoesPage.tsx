import { useState } from 'react'
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { useDebounce } from '@/hooks/useDebounce'
import {
  Bell,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  History,
  Users,
  Power,
  Search,
  Plus,
  Trash2,
  Edit2,
  Send,
  Eye,
  ChevronLeft,
  ChevronRight,
  ShieldAlert
} from 'lucide-react'
import { api } from '@/api/client'
import { useAuth } from '@/hooks/useAuth'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Label } from '@/components/ui/label'

export function NotificacoesPage() {
  const { user } = useAuth()
  const isAdmin = user?.permissoes?.admin
  const queryClient = useQueryClient()
  
  // States
  const [activeTab, setActiveTab] = useState('destinatarios')
  const [pagina, setPagina] = useState(1)
  const [logFiltroEvento, setLogFiltroEvento] = useState('')
  const [logFiltroStatus, setLogFiltroStatus] = useState('')
  const [modalDestinatarioOpen, setModalDestinatarioOpen] = useState(false)
  const [destinatarioEditando, setDestinatarioEditando] = useState<any>(null)
  const [modalDeleteOpen, setModalDeleteOpen] = useState(false)
  const [destinatarioParaDeletar, setDestinatarioParaDeletar] = useState<any>(null)
  const [confirmacaoExclusao, setConfirmacaoExclusao] = useState('')
  const [modalLogOpen, setModalLogOpen] = useState(false)
  const [logSelecionado, setLogSelecionado] = useState<any>(null)

  // Queries
  const { data: configData, isLoading: configLoading } = useQuery({
    queryKey: ['notificacoes', 'configuracoes'],
    queryFn: () => api.get<{ eventos: any[]; destinatarios: any[] }>('/api/v1/notificacoes/configuracoes/'),
  })

  const { data: logsData, isLoading: logsLoading, isFetching: logsFetching } = useQuery({
    queryKey: ['notificacoes', 'logs', pagina, logFiltroEvento, logFiltroStatus],
    queryFn: () => {
      const params = new URLSearchParams()
      params.set('page', String(pagina))
      params.set('page_size', '20')
      if (logFiltroEvento) params.set('evento', logFiltroEvento)
      if (logFiltroStatus) params.set('status', logFiltroStatus)
      return api.get<any>(`/api/v1/notificacoes/logs/?${params.toString()}`)
    },
    placeholderData: keepPreviousData,
  })

  // Mutations
  const toggleEventoMutation = useMutation({
    mutationFn: ({ event, enabled, audience }: { event: string, enabled?: boolean, audience?: string }) => 
      api.post(`/api/v1/notificacoes/eventos/${event}/toggle/`, { enabled, audience }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notificacoes', 'configuracoes'] })
      toast.success('Configuração de evento atualizada')
    },
    onError: () => toast.error('Erro ao atualizar configuração')
  })

  const salvarDestinatarioMutation = useMutation({
    mutationFn: (data: any) => {
      if (destinatarioEditando) {
        return api.patch(`/api/v1/notificacoes/destinatarios/${destinatarioEditando.id}/`, data)
      }
      return api.post('/api/v1/notificacoes/destinatarios/', data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notificacoes', 'configuracoes'] })
      toast.success(destinatarioEditando ? 'Destinatário atualizado' : 'Destinatário criado')
      setModalDestinatarioOpen(false)
    },
    onError: (error: any) => toast.error(error.message || 'Erro ao salvar destinatário')
  })

  const deletarDestinatarioMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/api/v1/notificacoes/destinatarios/${id}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notificacoes', 'configuracoes'] })
      toast.success('Destinatário excluído')
      setModalDeleteOpen(false)
      setConfirmacaoExclusao('')
    },
    onError: (error: any) => toast.error(error.message || 'Erro ao excluir destinatário')
  })
  
  const testarNotificacaoMutation = useMutation({
    mutationFn: (audience_key: string) => 
      api.post('/api/v1/notificacoes/teste/', { audience: audience_key, message: `Teste disparado pelo usuário ${user?.nome_completo}` }),
    onSuccess: () => {
      toast.success('Notificação de teste enviada para fila')
      queryClient.invalidateQueries({ queryKey: ['notificacoes', 'logs'] })
    },
    onError: (error: any) => toast.error(error.message || 'Erro ao enviar notificação')
  })

  const eventos = configData?.eventos || []
  const destinatarios = configData?.destinatarios || []
  const logs = logsData?.itens || []
  const paginacao = logsData?.paginacao || { pagina_atual: 1, total_paginas: 1, tem_proxima: false, tem_anterior: false }

  const handleSalvarDestinatario = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    salvarDestinatarioMutation.mutate({
      nome: formData.get('nome'),
      telefone: formData.get('telefone'),
      audience_key: formData.get('audience_key'),
    })
  }

  const getSeverityBadge = (severity: string) => {
    switch(severity) {
      case 'critical': return <Badge variant="destructive"><AlertTriangle className="w-3 h-3 mr-1" /> Crítico</Badge>
      case 'warning': return <Badge variant="warning"><AlertTriangle className="w-3 h-3 mr-1" /> Aviso</Badge>
      default: return <Badge variant="secondary">Info</Badge>
    }
  }

  if (!isAdmin && activeTab !== 'logs') {
    // Non-admins only see logs
    if (activeTab !== 'logs') setActiveTab('logs')
  }

  return (
    <div className="flex-1 overflow-auto bg-background/95">
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <Bell className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Notificações</h1>
            <p className="text-muted-foreground">Gerencie destinatários, eventos e acompanhe o histórico de disparos no n8n.</p>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="bg-muted/50 p-1">
            {isAdmin && (
              <>
                <TabsTrigger value="destinatarios" className="rounded-md">
                  <Users className="w-4 h-4 mr-2" /> Destinatários
                </TabsTrigger>
                <TabsTrigger value="eventos" className="rounded-md">
                  <ShieldAlert className="w-4 h-4 mr-2" /> Eventos do Sistema
                </TabsTrigger>
              </>
            )}
            <TabsTrigger value="logs" className="rounded-md">
              <History className="w-4 h-4 mr-2" /> Histórico de Envios
            </TabsTrigger>
          </TabsList>

          {isAdmin && (
            <>
              <TabsContent value="destinatarios" className="space-y-4 outline-none">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">Grupos e Destinatários</h2>
                  <Button onClick={() => {
                    setDestinatarioEditando(null)
                    setModalDestinatarioOpen(true)
                  }}>
                    <Plus className="w-4 h-4 mr-2" /> Adicionar Destinatário
                  </Button>
                </div>
                
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {destinatarios.map((dest: any) => (
                    <Card key={dest.id} className={!dest.ativo ? 'opacity-70' : ''}>
                      <CardHeader className="pb-3 flex flex-row items-start justify-between space-y-0">
                        <div>
                          <CardTitle className="text-base">{dest.nome}</CardTitle>
                          <CardDescription className="font-mono mt-1 text-xs">{dest.telefone}</CardDescription>
                        </div>
                        <Switch 
                          checked={dest.ativo} 
                          onCheckedChange={(checked) => salvarDestinatarioMutation.mutate({ ativo: checked })}
                          onClick={() => setDestinatarioEditando(dest)}
                        />
                      </CardHeader>
                      <CardContent>
                        <div className="flex items-center justify-between mt-2">
                          <Badge variant="outline" className="font-mono text-xs">{dest.audience_key}</Badge>
                          <div className="flex gap-2">
                            <Button size="icon" variant="ghost" className="h-8 w-8 text-muted-foreground" onClick={() => {
                              setDestinatarioEditando(dest)
                              setModalDestinatarioOpen(true)
                            }}>
                              <Edit2 className="w-4 h-4" />
                            </Button>
                            <Button size="icon" variant="ghost" className="h-8 w-8 text-primary" onClick={() => testarNotificacaoMutation.mutate(dest.audience_key)}>
                              <Send className="w-4 h-4" />
                            </Button>
                            <Button size="icon" variant="ghost" className="h-8 w-8 text-destructive" onClick={() => {
                              setDestinatarioParaDeletar(dest)
                              setModalDeleteOpen(true)
                            }}>
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                  {destinatarios.length === 0 && !configLoading && (
                    <div className="col-span-full py-12 text-center border-2 border-dashed rounded-xl text-muted-foreground">
                      <Users className="w-12 h-12 mx-auto mb-3 opacity-20" />
                      <p>Nenhum destinatário cadastrado.</p>
                    </div>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="eventos" className="space-y-4 outline-none">
                <div className="space-y-4">
                  {eventos.map((ev: any) => (
                    <Card key={ev.event}>
                      <CardContent className="p-6">
                        <div className="flex items-center justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h3 className="font-semibold text-lg">{ev.description}</h3>
                              {ev.event === 'stock.zero' ? getSeverityBadge('critical') : getSeverityBadge('warning')}
                              <Badge variant="outline" className="font-mono">{ev.event}</Badge>
                            </div>
                            <p className="text-sm text-muted-foreground">
                              Define qual grupo de WhatsApp será notificado quando este evento ocorrer no sistema.
                            </p>
                          </div>
                          
                          <div className="flex items-center gap-6">
                            <div className="w-64">
                              <Label className="text-xs mb-1.5 block text-muted-foreground">Roteamento (Audience)</Label>
                              <Select
                                value={ev.audience}
                                onValueChange={(val) => toggleEventoMutation.mutate({ event: ev.event, audience: val })}
                              >
                                <SelectTrigger>
                                  <SelectValue placeholder="Selecione..." />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="admin">Administradores (Padrão)</SelectItem>
                                  <SelectItem value="purchasing">Compras (Padrão)</SelectItem>
                                  {destinatarios.map((d: any) => (
                                    <SelectItem key={d.audience_key} value={d.audience_key}>
                                      {d.nome} ({d.audience_key})
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                            <div className="flex flex-col items-center">
                              <Label className="text-xs mb-1.5 block text-muted-foreground">Status</Label>
                              <Switch 
                                checked={ev.enabled}
                                onCheckedChange={(checked) => toggleEventoMutation.mutate({ event: ev.event, enabled: checked })}
                              />
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </TabsContent>
            </>
          )}

          <TabsContent value="logs" className="space-y-4 outline-none">
            <Card>
              <CardHeader className="py-4 border-b">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex gap-2 flex-1">
                    <Select value={logFiltroEvento} onValueChange={setLogFiltroEvento}>
                      <SelectTrigger className="w-[200px]">
                        <SelectValue placeholder="Todos os eventos" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="">Todos os eventos</SelectItem>
                        <SelectItem value="stock.low">Estoque Baixo</SelectItem>
                        <SelectItem value="stock.zero">Estoque Zerado</SelectItem>
                        <SelectItem value="teste_sistema">Teste de Sistema</SelectItem>
                      </SelectContent>
                    </Select>
                    <Select value={logFiltroStatus} onValueChange={setLogFiltroStatus}>
                      <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="Qualquer status" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="">Qualquer status</SelectItem>
                        <SelectItem value="sucesso">Sucesso</SelectItem>
                        <SelectItem value="erro">Erro</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardHeader>
              <div className="relative">
                {logsFetching && (
                  <div className="absolute inset-0 bg-background/50 flex items-center justify-center z-10">
                    <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  </div>
                )}
                <div className="divide-y border-b">
                  {logs.map((log: any) => (
                    <div key={log.id} className="flex items-center justify-between p-4 hover:bg-muted/50 transition-colors">
                      <div className="flex items-start gap-4">
                        <div className="mt-1">
                          {log.sucesso ? (
                            <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                          ) : (
                            <XCircle className="w-5 h-5 text-destructive" />
                          )}
                        </div>
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium">{log.event}</span>
                            {getSeverityBadge(log.severity)}
                            <Badge variant="outline" className="text-xs font-mono">{log.audience}</Badge>
                          </div>
                          <div className="text-sm text-muted-foreground flex gap-4">
                            <span>{new Date(log.created_at).toLocaleString('pt-BR')}</span>
                            {log.http_status && <span>HTTP {log.http_status}</span>}
                          </div>
                          {log.erro && (
                            <p className="text-sm text-destructive mt-1 font-medium">{log.erro}</p>
                          )}
                        </div>
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => {
                        setLogSelecionado(log)
                        setModalLogOpen(true)
                      }}>
                        <Eye className="w-4 h-4 mr-2" /> Detalhes
                      </Button>
                    </div>
                  ))}
                  {logs.length === 0 && !logsLoading && (
                    <div className="py-12 text-center text-muted-foreground">
                      <History className="w-12 h-12 mx-auto mb-3 opacity-20" />
                      <p>Nenhum log de notificação encontrado.</p>
                    </div>
                  )}
                </div>
              </div>
              <div className="p-4 flex items-center justify-between text-sm text-muted-foreground">
                <div>
                  Mostrando página {paginacao.pagina_atual} de {paginacao.total_paginas} (Total: {paginacao.total_itens})
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!paginacao.tem_anterior}
                    onClick={() => setPagina(p => p - 1)}
                  >
                    <ChevronLeft className="w-4 h-4 mr-1" /> Anterior
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!paginacao.tem_proxima}
                    onClick={() => setPagina(p => p + 1)}
                  >
                    Próxima <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                </div>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Modals */}
      <Dialog open={modalDestinatarioOpen} onOpenChange={setModalDestinatarioOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{destinatarioEditando ? 'Editar Destinatário' : 'Novo Destinatário'}</DialogTitle>
            <DialogDescription>Cadastre o telefone WhatsApp e a chave de roteamento do n8n.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSalvarDestinatario} className="space-y-4 mt-2">
            <div className="space-y-2">
              <Label>Nome do Grupo/Pessoa</Label>
              <Input name="nome" defaultValue={destinatarioEditando?.nome} placeholder="Ex: Compras" required />
            </div>
            <div className="space-y-2">
              <Label>Telefone WhatsApp</Label>
              <Input name="telefone" defaultValue={destinatarioEditando?.telefone} placeholder="Ex: +5511999999999" required />
            </div>
            <div className="space-y-2">
              <Label>Chave de Roteamento (Audience Key)</Label>
              <Input 
                name="audience_key" 
                defaultValue={destinatarioEditando?.audience_key} 
                placeholder="Ex: purchasing" 
                required 
                className="font-mono text-sm"
              />
              <p className="text-xs text-muted-foreground">Use apenas letras, números e underline.</p>
            </div>
            <DialogFooter className="mt-6">
              <Button type="button" variant="ghost" onClick={() => setModalDestinatarioOpen(false)}>Cancelar</Button>
              <Button type="submit" disabled={salvarDestinatarioMutation.isPending}>Salvar</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={modalDeleteOpen} onOpenChange={setModalDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-destructive">Excluir Destinatário</DialogTitle>
            <DialogDescription>
              Você está prestes a excluir <b>{destinatarioParaDeletar?.nome}</b>. Esta ação não pode ser desfeita.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4">
            <Label>Digite EXCLUIR para confirmar</Label>
            <Input 
              value={confirmacaoExclusao} 
              onChange={(e) => setConfirmacaoExclusao(e.target.value)}
              placeholder="EXCLUIR"
            />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setModalDeleteOpen(false)}>Cancelar</Button>
            <Button 
              variant="destructive" 
              disabled={confirmacaoExclusao !== 'EXCLUIR' || deletarDestinatarioMutation.isPending}
              onClick={() => deletarDestinatarioMutation.mutate(destinatarioParaDeletar?.id)}
            >
              Excluir Destinatário
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={modalLogOpen} onOpenChange={setModalLogOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Detalhes do Log</DialogTitle>
            <DialogDescription>UUID: {logSelecionado?.event_id}</DialogDescription>
          </DialogHeader>
          {logSelecionado && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm bg-muted/30 p-4 rounded-lg">
                <div><span className="text-muted-foreground">Evento:</span> <span className="font-medium">{logSelecionado.event}</span></div>
                <div><span className="text-muted-foreground">Audience:</span> <span className="font-medium">{logSelecionado.audience}</span></div>
                <div><span className="text-muted-foreground">Status:</span> {logSelecionado.sucesso ? <span className="text-emerald-500 font-medium">Sucesso</span> : <span className="text-destructive font-medium">Erro</span>}</div>
                <div><span className="text-muted-foreground">Data/Hora:</span> {new Date(logSelecionado.created_at).toLocaleString('pt-BR')}</div>
                <div><span className="text-muted-foreground">HTTP Status:</span> {logSelecionado.http_status || '-'}</div>
                <div><span className="text-muted-foreground">Severidade:</span> {getSeverityBadge(logSelecionado.severity)}</div>
              </div>
              
              {logSelecionado.erro && (
                <div>
                  <h4 className="text-sm font-semibold mb-2 text-destructive">Mensagem de Erro</h4>
                  <pre className="bg-destructive/10 text-destructive p-3 rounded-md text-xs whitespace-pre-wrap font-mono">
                    {logSelecionado.erro}
                  </pre>
                </div>
              )}

              <div>
                <h4 className="text-sm font-semibold mb-2">Payload JSON Enviado</h4>
                <pre className="bg-muted p-3 rounded-md text-xs overflow-auto max-h-[300px] font-mono">
                  {JSON.stringify(logSelecionado.payload, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
