import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from notifications.client import NotificationClient

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
