from decimal import Decimal
import logging

from .client import NotificationClient
from .models import NotificationEventConfig


STOCK_LOW = 'stock.low'
STOCK_ZERO = 'stock.zero'
SOURCE_SGE = 'sge'

logger = logging.getLogger(__name__)


def _to_decimal(value):
    if value is None:
        return None
    return Decimal(str(value))


def _to_payload_number(value):
    if value is None:
        return None
    return float(Decimal(str(value)))


def determine_stock_event(previous_stock, current_stock, minimum_stock=None):
    previous_stock = _to_decimal(previous_stock)
    current_stock = _to_decimal(current_stock)
    minimum_stock = _to_decimal(minimum_stock)

    if previous_stock > 0 and current_stock <= 0:
        return STOCK_ZERO

    if minimum_stock is None:
        return None

    if previous_stock > minimum_stock and current_stock <= minimum_stock:
        return STOCK_LOW

    return None


def get_event_config(event):
    try:
        return NotificationEventConfig.objects.get(event=event)
    except NotificationEventConfig.DoesNotExist:
        logger.warning(
            'Configuracao de evento de notificacao nao encontrada.',
            extra={'event': event},
        )
        return None


def notify_stock_threshold_crossed(
    *,
    product_id,
    product,
    previous_stock,
    current_stock,
    minimum_stock,
    unit,
):
    event = determine_stock_event(previous_stock, current_stock, minimum_stock)
    if event is None:
        return False

    config = get_event_config(event)
    if config is None or not config.enabled:
        return False

    data = {
        'product_id': product_id,
        'product': product,
        'current_stock': _to_payload_number(current_stock),
        'unit': unit,
    }
    if event == STOCK_LOW:
        data['minimum_stock'] = _to_payload_number(minimum_stock)

    return NotificationClient.send(
        event=event,
        source=SOURCE_SGE,
        audience=config.audience,
        data=data,
    )
