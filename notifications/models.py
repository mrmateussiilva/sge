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


class NotificationRecipient(models.Model):
    nome = models.CharField(max_length=150)
    telefone = models.CharField(max_length=20)
    audience_key = models.CharField(max_length=100, unique=True)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'destinatário de notificação'
        verbose_name_plural = 'destinatários de notificações'

    def __str__(self):
        return f'{self.nome} ({self.audience_key})'


class NotificationLog(models.Model):
    event = models.CharField(max_length=100)
    event_id = models.UUIDField()
    severity = models.CharField(max_length=50)
    audience = models.CharField(max_length=100)
    sucesso = models.BooleanField()
    payload = models.JSONField(blank=True, null=True)
    http_status = models.IntegerField(blank=True, null=True)
    erro = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'log de notificação'
        verbose_name_plural = 'logs de notificações'

    def __str__(self):
        return f'{self.event} -> {self.audience} (Sucesso: {self.sucesso})'
