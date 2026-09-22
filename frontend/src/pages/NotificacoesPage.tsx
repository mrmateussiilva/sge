import { useState } from 'react'
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import {
  Bell,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  History,
  Users,
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
import { toast } from 'sonner'
import { Modal } from '@/components/ui/modal'

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

        <div className="space-y-6">
          <div className="flex space-x-2 bg-muted/50 p-1 rounded-md">
            {isAdmin && (
              <>
                <button onClick={() => setActiveTab("destinatarios")} className={`flex items-center px-3 py-1.5 text-sm font-medium rounded-md transition-all ${activeTab === "destinatarios" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:bg-muted"}`} type="button"><Users className="w-4 h-4 mr-2" /> Destinatários</button>
                <button onClick={() => setActiveTab("eventos")} className={`flex items-center px-3 py-1.5 text-sm font-medium rounded-md transition-all ${activeTab === "eventos" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:bg-muted"}`} type="button"><ShieldAlert className="w-4 h-4 mr-2" /> Eventos do Sistema</button>
              </>
            )}
            <button onClick={() => setActiveTab("logs")} className={`flex items-center px-3 py-1.5 text-sm font-medium rounded-md transition-all ${activeTab === "logs" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:bg-muted"}`} type="button"><History className="w-4 h-4 mr-2" /> Histórico de Envios</button>
          </div>

          {isAdmin && (
            <>
              {activeTab === "destinatarios" && (<div className="space-y-4 outline-none">
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
                        <input type="checkbox" className="w-4 h-4 cursor-pointer" checked={dest.ativo} onChange={(e) => ((checked) => salvarDestinatarioMutation.mutate({ ativo: checked }))(e.target.checked)} onClick={() => setDestinatarioEditando(dest)} />
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
              </div>)}

              {activeTab === "eventos" && (<div className="space-y-4 outline-none">
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
                              <label className="text-xs mb-1.5 block text-muted-foreground">Roteamento (Audience)</label>
                              <select value={ev.audience} onChange={(e) => ((val) => toggleEventoMutation.mutate({ event: ev.event, audience: val }))(e.target.value)} className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
                                
                                  <option value="" disabled>Selecione...</option>
                                
                                
                                  <option value="admin">Administradores (Padrão)</option>
                                  <option value="purchasing">Compras (Padrão)</option>
                                  {destinatarios.map((d: any) => (
                                    <option key={d.audience_key} value={d.audience_key}>
                                      {d.nome} ({d.audience_key})
                                    </option>
                                  ))}
                                
                              </select>
                            </div>
                            <div className="flex flex-col items-center">
                              <label className="text-xs mb-1.5 block text-muted-foreground">Status</label>
                              <input type="checkbox" className="w-4 h-4 cursor-pointer" checked={ev.enabled} onChange={(e) => ((checked) => toggleEventoMutation.mutate({ event: ev.event, enabled: checked }))(e.target.checked)} />
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>)}
            </>
          )}

          {activeTab === "logs" && (<div className="space-y-4 outline-none">
            <Card>
              <CardHeader className="py-4 border-b">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex gap-2 flex-1">
                    <select value={logFiltroEvento} onChange={(e) => (setLogFiltroEvento)(e.target.value)} className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
                      
                        <option value="" disabled>Todos os eventos</option>
                      
                      
                        <option value="">Todos os eventos</option>
                        <option value="stock.low">Estoque Baixo</option>
                        <option value="stock.zero">Estoque Zerado</option>
                        <option value="teste_sistema">Teste de Sistema</option>
                      
                    </select>
                    <select value={logFiltroStatus} onChange={(e) => (setLogFiltroStatus)(e.target.value)} className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
                      
                        <option value="" disabled>Qualquer status</option>
                      
                      
                        <option value="">Qualquer status</option>
                        <option value="sucesso">Sucesso</option>
                        <option value="erro">Erro</option>
                      
                    </select>
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
          </div>)}
        </div>
      </div>

      {/* Modals */}
      <Modal isOpen={modalDestinatarioOpen} onClose={() => setModalDestinatarioOpen(false)} title={destinatarioEditando ? 'Editar Destinatário' : 'Novo Destinatário'} description="Cadastre o telefone WhatsApp e a chave de roteamento do n8n.">
        
          
            
            
          
          <form onSubmit={handleSalvarDestinatario} className="space-y-4 mt-2">
            <div className="space-y-2">
              <label>Nome do Grupo/Pessoa</label>
              <Input name="nome" defaultValue={destinatarioEditando?.nome} placeholder="Ex: Compras" required />
            </div>
            <div className="space-y-2">
              <label>Telefone WhatsApp</label>
              <Input name="telefone" defaultValue={destinatarioEditando?.telefone} placeholder="Ex: +5511999999999" required />
            </div>
            <div className="space-y-2">
              <label>Chave de Roteamento (Audience Key)</label>
              <Input 
                name="audience_key" 
                defaultValue={destinatarioEditando?.audience_key} 
                placeholder="Ex: purchasing" 
                required 
                className="font-mono text-sm"
              />
              <p className="text-xs text-muted-foreground">Use apenas letras, números e underline.</p>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <Button type="button" variant="ghost" onClick={() => setModalDestinatarioOpen(false)}>Cancelar</Button>
              <Button type="submit" disabled={salvarDestinatarioMutation.isPending}>Salvar</Button>
            </div>
          </form>
        
      </Modal>

      <Modal isOpen={modalDeleteOpen} onClose={() => setModalDeleteOpen(false)} title="Excluir Destinatário" description={<>Você está prestes a excluir <b>{destinatarioParaDeletar?.nome}</b>. Esta ação não pode ser desfeita.</>}>
        
          
            
            
          
          <div className="space-y-3 py-4">
            <label>Digite EXCLUIR para confirmar</label>
            <Input 
              value={confirmacaoExclusao} 
              onChange={(e) => setConfirmacaoExclusao(e.target.value)}
              placeholder="EXCLUIR"
            />
          </div>
          <div className="mt-6 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setModalDeleteOpen(false)}>Cancelar</Button>
            <Button 
              variant="destructive" 
              disabled={confirmacaoExclusao !== 'EXCLUIR' || deletarDestinatarioMutation.isPending}
              onClick={() => deletarDestinatarioMutation.mutate(destinatarioParaDeletar?.id)}
            >
              Excluir Destinatário
            </Button>
          </div>
        
      </Modal>

      <Modal isOpen={modalLogOpen} onClose={() => setModalLogOpen(false)} title="Detalhes do Log" description={`UUID: ${logSelecionado?.event_id}`}>
        <div className="max-w-3xl">
          
            
            
          
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
        </div>
      </Modal>
    </div>
  )
}
