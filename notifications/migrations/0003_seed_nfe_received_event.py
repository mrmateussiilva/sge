from django.db import migrations


def seed_nfe_received_event(apps, schema_editor):
    NotificationEventConfig = apps.get_model('notifications', 'NotificationEventConfig')
    NotificationEventConfig.objects.update_or_create(
        event='nfe.received',
        defaults={
            'description': 'Nova NF-e de Fornecedor Recebida',
            'enabled': True,
            'audience': 'purchasing',
        },
    )


def unseed_nfe_received_event(apps, schema_editor):
    NotificationEventConfig = apps.get_model('notifications', 'NotificationEventConfig')
    NotificationEventConfig.objects.filter(event='nfe.received').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('notifications', '0002_notificationlog_notificationrecipient'),
    ]

    operations = [
        migrations.RunPython(seed_nfe_received_event, unseed_nfe_received_event),
    ]
