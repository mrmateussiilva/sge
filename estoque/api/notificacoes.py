import json
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie

from notifications.models import NotificationEventConfig, NotificationRecipient, NotificationLog
from notifications.client import NotificationClient


def _is_admin(user):
    return getattr(user, 'permissoes', {}).get('admin', False)


@login_required
@require_http_methods(['GET'])
def listar_configuracoes(request):
    eventos = NotificationEventConfig.objects.all()
    destinatarios = NotificationRecipient.objects.all()

    dados_eventos = [
        {
            'event': ev.event,
            'description': ev.description,
            'enabled': ev.enabled,
            'audience': ev.audience,
        }
        for ev in eventos
    ]

    dados_destinatarios = [
        {
            'id': dest.id,
            'nome': dest.nome,
            'telefone': dest.telefone,
            'audience_key': dest.audience_key,
            'ativo': dest.ativo,
        }
        for dest in destinatarios
    ]

    return JsonResponse({
        'ok': True,
        'eventos': dados_eventos,
        'destinatarios': dados_destinatarios,
    })


@login_required
@require_http_methods(['POST'])
def toggle_evento(request, event_name):
    if not _is_admin(request.user):
        return JsonResponse({'ok': False, 'erro': 'Acesso negado'}, status=403)

    try:
        data = json.loads(request.body)
        evento = NotificationEventConfig.objects.get(event=event_name)
        
        if 'enabled' in data:
            evento.enabled = data['enabled']
        if 'audience' in data:
            evento.audience = data['audience']
            
        evento.save()
        return JsonResponse({'ok': True})
    except NotificationEventConfig.DoesNotExist:
        return JsonResponse({'ok': False, 'erro': 'Evento não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'erro': str(e)}, status=400)


@login_required
@require_http_methods(['GET', 'POST'])
def gerenciar_destinatarios(request):
    if request.method == 'GET':
        destinatarios = NotificationRecipient.objects.all()
        dados = [
            {
                'id': dest.id,
                'nome': dest.nome,
                'telefone': dest.telefone,
                'audience_key': dest.audience_key,
                'ativo': dest.ativo,
            }
            for dest in destinatarios
        ]
        return JsonResponse({'ok': True, 'itens': dados})
        
    elif request.method == 'POST':
        if not _is_admin(request.user):
            return JsonResponse({'ok': False, 'erro': 'Acesso negado'}, status=403)
            
        try:
            data = json.loads(request.body)
            destinatario = NotificationRecipient.objects.create(
                nome=data['nome'],
                telefone=data['telefone'],
                audience_key=data['audience_key'],
                ativo=data.get('ativo', True)
            )
            return JsonResponse({
                'ok': True, 
                'id': destinatario.id,
                'nome': destinatario.nome,
                'telefone': destinatario.telefone,
                'audience_key': destinatario.audience_key,
                'ativo': destinatario.ativo
            }, status=201)
        except Exception as e:
            return JsonResponse({'ok': False, 'erro': str(e)}, status=400)


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def detalhe_destinatario(request, destinatario_id):
    if not _is_admin(request.user):
        return JsonResponse({'ok': False, 'erro': 'Acesso negado'}, status=403)

    try:
        destinatario = NotificationRecipient.objects.get(id=destinatario_id)
    except NotificationRecipient.DoesNotExist:
        return JsonResponse({'ok': False, 'erro': 'Destinatário não encontrado'}, status=404)
        
    if request.method == 'PATCH':
        try:
            data = json.loads(request.body)
            if 'nome' in data:
                destinatario.nome = data['nome']
            if 'telefone' in data:
                destinatario.telefone = data['telefone']
            if 'audience_key' in data:
                destinatario.audience_key = data['audience_key']
            if 'ativo' in data:
                destinatario.ativo = data['ativo']
                
            destinatario.save()
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'ok': False, 'erro': str(e)}, status=400)
            
    elif request.method == 'DELETE':
        destinatario.delete()
        return JsonResponse({'ok': True})


@login_required
@require_http_methods(['GET'])
def listar_logs(request):
    logs = NotificationLog.objects.all()
    
    # Filtros
    evento = request.GET.get('evento')
    if evento:
        logs = logs.filter(event=evento)
        
    status = request.GET.get('status')
    if status == 'sucesso':
        logs = logs.filter(sucesso=True)
    elif status == 'erro':
        logs = logs.filter(sucesso=False)
        
    # Paginação
    try:
        page_num = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
    except ValueError:
        page_num = 1
        page_size = 20
        
    paginator = Paginator(logs, page_size)
    page_obj = paginator.get_page(page_num)
    
    dados = [
        {
            'id': log.id,
            'event': log.event,
            'event_id': str(log.event_id),
            'severity': log.severity,
            'audience': log.audience,
            'sucesso': log.sucesso,
            'payload': log.payload,
            'http_status': log.http_status,
            'erro': log.erro,
            'created_at': log.created_at.isoformat(),
        }
        for log in page_obj
    ]
    
    return JsonResponse({
        'ok': True,
        'itens': dados,
        'paginacao': {
            'pagina_atual': page_obj.number,
            'total_paginas': paginator.num_pages,
            'total_itens': paginator.count,
            'tem_proxima': page_obj.has_next(),
            'tem_anterior': page_obj.has_previous(),
        }
    })


@login_required
@require_POST
def disparar_teste_notificacao(request):
    try:
        data = json.loads(request.body)
        audience = data.get('audience', 'admin')
        mensagem = data.get('mensagem', 'Este é um teste de notificação do SGE!')
    except Exception:
        audience = 'admin'
        mensagem = 'Este é um teste genérico de notificação do SGE!'
        
    sucesso = NotificationClient.send(
        event='teste_sistema',
        audience=audience,
        data={
            'mensagem': mensagem,
            'usuario': request.user.username
        }
    )

    if sucesso:
        return JsonResponse({'ok': True, 'mensagem': 'Evento enviado para o Webhook com sucesso!'})
    else:
        return JsonResponse({'ok': False, 'erro': 'Falha ao comunicar com o webhook. Verifique os logs e as variáveis de ambiente.'}, status=500)
