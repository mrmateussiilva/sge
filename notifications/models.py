from django.db import models


class NotificationEventConfig(models.Model):
    event = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=200)
    enabled = models.BooleanField(default=True)
    audience = models.CharField(max_length=100)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['event']
        verbose_name = 'configuração de evento de notificação'
        verbose_name_plural = 'configurações de eventos de notificação'

    def __str__(self):
        return f'{self.event} - {self.description}'
