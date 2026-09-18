from django.db import migrations, models


INITIAL_EVENTS = {
    'stock.low': {
        'description': 'Estoque baixo',
        'enabled': True,
        'audience': 'purchasing',
    },
    'stock.zero': {
        'description': 'Estoque zerado',
        'enabled': True,
        'audience': 'purchasing',
    },
}


def seed_notification_events(apps, schema_editor):
    NotificationEventConfig = apps.get_model('notifications', 'NotificationEventConfig')
    for event, defaults in INITIAL_EVENTS.items():
        NotificationEventConfig.objects.update_or_create(event=event, defaults=defaults)


def unseed_notification_events(apps, schema_editor):
    NotificationEventConfig = apps.get_model('notifications', 'NotificationEventConfig')
    NotificationEventConfig.objects.filter(event__in=INITIAL_EVENTS.keys()).delete()


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='NotificationEventConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event', models.CharField(max_length=100, unique=True)),
                ('description', models.CharField(max_length=200)),
                ('enabled', models.BooleanField(default=True)),
                ('audience', models.CharField(max_length=100)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'configuração de evento de notificação',
                'verbose_name_plural': 'configurações de eventos de notificação',
                'ordering': ['event'],
            },
        ),
        migrations.RunPython(seed_notification_events, unseed_notification_events),
    ]
