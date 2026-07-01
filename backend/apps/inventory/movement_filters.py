import uuid

from rest_framework.exceptions import ValidationError

from apps.inventory.financial_product_filters import parse_search
from apps.inventory.models import MovementReason

VALID_MOVEMENT_REASONS = frozenset(choice.value for choice in MovementReason)


def parse_movement_reasons(value: str | None) -> list[str] | None:
    if value is None or value == '':
        return None

    parts = [part.strip() for part in value.split(',') if part.strip()]
    invalid = [part for part in parts if part not in VALID_MOVEMENT_REASONS]
    if invalid:
        raise ValidationError(
            {
                'detail': (
                    'Invalid reason. Choose one or more of: '
                    f'{", ".join(sorted(VALID_MOVEMENT_REASONS))}.'
                )
            }
        )
    return parts


def parse_product_id(value: str | None) -> int | None:
    if value is None or value == '':
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValidationError({'detail': 'Invalid product id.'}) from exc


def parse_stock_batch_id(value: str | None) -> uuid.UUID | None:
    if value is None or value == '':
        return None
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise ValidationError({'detail': 'Invalid stock_batch id.'}) from exc


__all__ = [
    'parse_movement_reasons',
    'parse_product_id',
    'parse_search',
    'parse_stock_batch_id',
]
