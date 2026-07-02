from rest_framework.exceptions import ValidationError

from apps.orders.models import OrderStatus

VALID_ORDER_STATUSES = frozenset(OrderStatus.values)


def parse_order_status(value: str | None) -> str | None:
    if value is None or value == '':
        return None
    normalized = value.upper()
    if normalized not in VALID_ORDER_STATUSES:
        raise ValidationError(
            {
                'detail': (
                    'Invalid status. Choose one of: '
                    f'{", ".join(sorted(VALID_ORDER_STATUSES))}.'
                )
            }
        )
    return normalized
