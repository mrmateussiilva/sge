from django.contrib import admin, messages

from .client import NotificationClient
from .events import STOCK_LOW, STOCK_ZERO
from .models import NotificationEventConfig


def test_payload_for_event(event):
    if event == STOCK_LOW:
        return {
            'product_id': 0,
            'product': 'Produto de teste',
            'current_stock': 10,
            'minimum_stock': 20,
            'unit': 'un',
        }
    if event == STOCK_ZERO:
        return {
            'product_id': 0,
            'product': 'Produto de teste',
            'current_stock': 0,
            'unit': 'un',
        }
    return None


@admin.register(NotificationEventConfig)
class NotificationEventConfigAdmin(admin.ModelAdmin):
    list_display = ('event', 'description', 'enabled', 'audience', 'updated_at')
    list_editable = ('enabled',)
    list_filter = ('enabled',)
    search_fields = ('event', 'description', 'audience')
    ordering = ('event',)
    fields = ('event', 'description', 'enabled', 'audience')
    actions = ('send_test_notification',)

    @admin.action(description='Enviar notificação de teste')
    def send_test_notification(self, request, queryset):
        sent = 0
        failed = 0
        unknown = 0

        for config in queryset:
            payload = test_payload_for_event(config.event)
            if payload is None:
                unknown += 1
                continue

            ok = NotificationClient.send(
                event=config.event,
                source='sge',
                audience=config.audience,
                data=payload,
            )
            if ok:
                sent += 1
            else:
                failed += 1

        if sent:
            self.message_user(
                request,
                f'{sent} notificação(ões) de teste enviada(s). A ação de teste ignora se o evento está ativo.',
                level=messages.SUCCESS,
            )
        if failed:
            self.message_user(
                request,
                f'{failed} notificação(ões) de teste falharam. A ação de teste ignora se o evento está ativo.',
                level=messages.ERROR,
            )
        if unknown:
            self.message_user(
                request,
                f'{unknown} configuração(ões) sem payload de teste conhecido.',
                level=messages.WARNING,
            )
