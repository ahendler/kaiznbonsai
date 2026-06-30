from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.inventory.models import MovementReason, Stock, StockMovement


@transaction.atomic
def record_movement(
    *,
    user,
    stock_batch: Stock,
    delta: Decimal,
    reason: MovementReason,
    sales_order_item=None,
    purchase_order_item=None,
) -> StockMovement:
    """Append a movement row and update stock_batch.current_quantity atomically."""
    if stock_batch.user_id != user.id:
        raise ValidationError("Stock batch does not belong to this user.")

    movement = StockMovement.objects.create(
        user=user,
        stock_batch=stock_batch,
        delta=delta,
        reason=reason,
        sales_order_item=sales_order_item,
        purchase_order_item=purchase_order_item,
    )

    stock_batch.current_quantity += delta
    if stock_batch.current_quantity < 0:
        raise ValidationError("Stock quantity cannot be negative.")

    stock_batch.save_without_historical_record(
        update_fields=['current_quantity', 'updated_at'],
    )

    return movement
