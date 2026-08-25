from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):
    return JsonResponse({'ok': True, 'version': settings.APP_VERSION})
