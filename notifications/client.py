import json
import logging
import socket
import urllib.error
import urllib.request
import uuid

from django.conf import settings
from django.utils import timezone

from notifications.models import NotificationLog

logger = logging.getLogger(__name__)


class NotificationClient:
    timeout = 3

    @classmethod
    def send(cls, *, event, audience, data, severity='info', source='sge'):
        webhook_url = getattr(settings, 'NOTIFICATION_WEBHOOK_URL', '')
        token = 'mateus3010'  # TODO: mover para .env
        event_id = str(uuid.uuid4())

        if not webhook_url or not token:
            logger.debug(
                'Notificacao nao enviada: webhook ou token nao configurado.',
                extra={'event': event, 'event_id': event_id},
            )
            NotificationLog.objects.create(
                event=event,
                event_id=event_id,
                severity=severity,
                audience=audience,
                sucesso=False,
                erro='Webhook ou token não configurado'
            )
            return False

        payload = {
            'event_id': event_id,
            'event': event,
            'source': source,
            'audience': audience,
            'severity': severity,
            'occurred_at': timezone.now().isoformat(),
            'data': data,
        }
        body = json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(
            webhook_url,
            data=body,
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'X-Notify-Token': token,
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=cls.timeout) as response:
                if 200 <= response.status < 300:
                    NotificationLog.objects.create(
                        event=event,
                        event_id=event_id,
                        severity=severity,
                        audience=audience,
                        sucesso=True,
                        payload=payload,
                        http_status=response.status
                    )
                    return True
                logger.warning(
                    'Falha ao enviar evento de notificacao: status HTTP inesperado.',
                    extra={'event': event, 'event_id': event_id, 'status': response.status},
                )
                NotificationLog.objects.create(
                    event=event,
                    event_id=event_id,
                    severity=severity,
                    audience=audience,
                    sucesso=False,
                    payload=payload,
                    http_status=response.status,
                    erro='Status HTTP inesperado'
                )
                return False
        except urllib.error.HTTPError as exc:
            response_body = ''
            try:
                response_body = exc.read(300).decode('utf-8', errors='replace')
            except Exception:
                response_body = ''

            logger.warning(
                'Falha ao enviar evento de notificacao: erro HTTP status=%s event=%s event_id=%s body=%s',
                exc.code,
                event,
                event_id,
                response_body,
            )
            NotificationLog.objects.create(
                event=event,
                event_id=event_id,
                severity=severity,
                audience=audience,
                sucesso=False,
                payload=payload,
                http_status=exc.code,
                erro=response_body
            )
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
            logger.warning(
                'Falha ao enviar evento de notificacao.',
                extra={'event': event, 'event_id': event_id, 'error': exc.__class__.__name__},
            )
            NotificationLog.objects.create(
                event=event,
                event_id=event_id,
                severity=severity,
                audience=audience,
                sucesso=False,
                payload=payload,
                erro=str(exc)
            )
        return False
