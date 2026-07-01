from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.inventory.models import MovementReason, Stock, StockMovement

STOCK_BATCH_NOT_FOUND = 'Stock batch not found.'
BATCH_ALREADY_VOIDED = 'This stock batch has already been voided.'
BATCH_PO_LINKED = (
    'Cannot void a batch received from a purchase order. Cancel the purchase order instead.'
)
BATCH_NO_REMAINING_QTY = 'Cannot void a batch with no remaining quantity.'
BATCH_HAS_SALE_HISTORY = 'Cannot void a batch that has been used in a sale.'


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
        raise ValidationError(STOCK_BATCH_NOT_FOUND)

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


@transaction.atomic
def void_manual_stock_batch(*, user, stock_batch: Stock) -> Stock:
    """Void an unconsumed manual batch by appending VOID and setting voided_at."""
    if stock_batch.user_id != user.id:
        raise ValidationError(STOCK_BATCH_NOT_FOUND)

    stock_batch = Stock.objects.select_for_update().get(pk=stock_batch.pk)

    if stock_batch.voided_at is not None:
        raise ValidationError(BATCH_ALREADY_VOIDED)

    if stock_batch.purchase_order_item_id:
        raise ValidationError(BATCH_PO_LINKED)

    if stock_batch.current_quantity <= 0:
        raise ValidationError(BATCH_NO_REMAINING_QTY)

    if stock_batch.movements.filter(reason=MovementReason.SALE).exists():
        raise ValidationError(BATCH_HAS_SALE_HISTORY)

    record_movement(
        user=user,
        stock_batch=stock_batch,
        delta=-stock_batch.current_quantity,
        reason=MovementReason.VOID,
    )

    stock_batch.voided_at = timezone.now()
    stock_batch.save(update_fields=['voided_at', 'updated_at'])

    return stock_batch
