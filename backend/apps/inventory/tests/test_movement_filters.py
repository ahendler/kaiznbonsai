import pytest
from rest_framework.exceptions import ValidationError

from apps.inventory.movement_filters import VALID_MOVEMENT_REASONS, parse_movement_reasons
from apps.inventory.models import MovementReason, Stock


def test_stock_has_nullable_voided_at_field():
    field = Stock._meta.get_field('voided_at')
    assert field.null is True
    assert field.blank is True


@pytest.mark.parametrize(
    'value',
    [
        'VOID',
        'RECEIPT_REVERSAL',
        'RECEIPT,SALE,VOID',
        'RECEIPT_REVERSAL,RETURN',
    ],
)
def test_parse_movement_reasons_accepts_new_reasons(value):
    assert parse_movement_reasons(value) == value.split(',')


def test_valid_movement_reasons_includes_new_enum_values():
    assert MovementReason.VOID in VALID_MOVEMENT_REASONS
    assert MovementReason.RECEIPT_REVERSAL in VALID_MOVEMENT_REASONS


def test_parse_movement_reasons_rejects_unknown_reason():
    with pytest.raises(ValidationError):
        parse_movement_reasons('NOT_A_REASON')
