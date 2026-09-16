from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):
    return JsonResponse({'ok': True, 'version': settings.APP_VERSION})


@login_required
def spa_view(request, *args, **kwargs):
    """Serve a Single Page Application React para usuários autenticados."""
    index_file = settings.BASE_DIR / 'frontend' / 'dist' / 'index.html'
    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            return HttpResponse(f.read(), content_type='text/html')
    return HttpResponse(
        '<h1>Frontend SPA não compilado</h1>'
        '<p>Execute <code>npm run build</code> dentro da pasta <code>frontend/</code>.</p>',
        status=503,
        content_type='text/html',
    )
