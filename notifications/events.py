from decimal import Decimal
import logging

from .client import NotificationClient
from .models import NotificationEventConfig


STOCK_LOW = 'stock.low'
STOCK_ZERO = 'stock.zero'
NFE_RECEIVED = 'nfe.received'
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

    severity_map = {
        STOCK_LOW:  'warning',
        STOCK_ZERO: 'critical',
    }

    return NotificationClient.send(
        event=event,
        source=SOURCE_SGE,
        audience=config.audience,
        severity=severity_map.get(event, 'info'),
        data=data,
    )


def notify_nfe_received(
    *,
    numero_nfe: str,
    fornecedor_nome: str,
    valor_total: float | Decimal,
    chave_nfe: str = '',
):
    """
    Notifica destinatários configurados sobre uma nova NF-e de fornecedor recebida via Omie/SEFAZ.
    """
    config = get_event_config(NFE_RECEIVED)
    if config is None or not config.enabled:
        return False

    data = {
        'numero_nfe': str(numero_nfe or ''),
        'fornecedor': str(fornecedor_nome or ''),
        'valor_total': _to_payload_number(valor_total),
        'chave_nfe': str(chave_nfe or ''),
    }

    return NotificationClient.send(
        event=NFE_RECEIVED,
        source=SOURCE_SGE,
        audience=config.audience,
        severity='info',
        data=data,
    )

