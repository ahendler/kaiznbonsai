from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.orders.models import PurchaseOrder, PurchaseOrderItem, SalesOrder, SalesOrderItem, OrderStatus
from apps.inventory.models import Product, Stock, MovementReason, StockMovement
from apps.inventory.commands import record_movement
from apps.orders.validators import validate_products_belong_to_user
from apps.orders.allocation import available_batches_for_allocation
from apps.orders.constants import StockAllocationStrategy

ORDER_NOT_DRAFT = 'Only draft orders can be confirmed.'
ORDER_ALREADY_CANCELLED = 'Order is already cancelled.'
ORDER_CANCEL_UNAVAILABLE = (
    'Cannot cancel this order because no stock was deducted from inventory when it was confirmed.'
)


def _validate_products_belong_to_user(user, items_data: list) -> None:
    validate_products_belong_to_user(user, {item['product_id'] for item in items_data})

@transaction.atomic
def create_purchase_order(user, items_data: list, title: str = None, order_date=None) -> PurchaseOrder:
    """
    Creates a new PurchaseOrder in DRAFT status.
    items_data: [{'product_id': int, 'quantity': float, 'unit_cost': float, 'lot_code': str, 'best_before': date}]
    """
    if not items_data:
        raise ValidationError("A purchase order must have at least one item.")

    _validate_products_belong_to_user(user, items_data)

    order = PurchaseOrder.objects.create(
        user=user,
        title=title,
        status=OrderStatus.DRAFT,
        **( {'order_date': order_date} if order_date else {} )
    )
    
    for item in items_data:
        PurchaseOrderItem.objects.create(
            order=order,
            product_id=item['product_id'],
            quantity=item['quantity'],
            unit_cost=item['unit_cost'],
            lot_code=item.get('lot_code') or '',
            best_before=item.get('best_before')
        )
    return order

@transaction.atomic
def confirm_purchase_order(order: PurchaseOrder) -> PurchaseOrder:
    """
    Transitions PO to CONFIRMED.
    Iterates over items and creates Stock batches representing the received goods.
    """
    if order.status != OrderStatus.DRAFT:
        raise ValidationError(ORDER_NOT_DRAFT)

    for item in order.items.all():
        stock = Stock.objects.create(
            user=order.user,
            product=item.product,
            initial_quantity=item.quantity,
            current_quantity=Decimal('0'),
            unit_cost=item.unit_cost,
            lot_code=item.lot_code or f"PO{order.id}-ITEM{item.id}",
            best_before=item.best_before,
            purchase_order_item=item,
        )
        record_movement(
            user=order.user,
            stock_batch=stock,
            delta=Decimal(str(item.quantity)),
            reason=MovementReason.RECEIPT,
            purchase_order_item=item,
        )

    order.status = OrderStatus.CONFIRMED
    order.save(update_fields=['status', 'updated_at'])
    return order

@transaction.atomic
def cancel_purchase_order(order: PurchaseOrder) -> PurchaseOrder:
    """
    Transitions PO to CANCELLED.
    If CONFIRMED, voids each linked stock batch via RECEIPT_REVERSAL (ledger rows kept).
    If any Stock batch has been partially or fully consumed, it raises an error.
    """
    if order.status == OrderStatus.CANCELLED:
        raise ValidationError(ORDER_ALREADY_CANCELLED)

    if order.status == OrderStatus.CONFIRMED:
        stock_batches = Stock.objects.filter(purchase_order_item__order=order)
        batch_ids = list(stock_batches.values_list('pk', flat=True))
        list(Stock.objects.filter(id__in=batch_ids).select_for_update())

        for batch in Stock.objects.filter(id__in=batch_ids).select_related('purchase_order_item'):
            if batch.movements.filter(reason=MovementReason.SALE).exists():
                raise ValidationError(
                    "Cannot cancel: one or more stock batches have been used in a sale."
                )
            if batch.current_quantity < batch.initial_quantity:
                raise ValidationError(
                    "Cannot cancel a confirmed order because some of the received stock "
                    "has already been consumed or sold."
                )

            record_movement(
                user=order.user,
                stock_batch=batch,
                delta=-batch.current_quantity,
                reason=MovementReason.RECEIPT_REVERSAL,
                purchase_order_item=batch.purchase_order_item,
            )
            batch.voided_at = timezone.now()
            batch.save(update_fields=['voided_at', 'updated_at'])

    order.status = OrderStatus.CANCELLED
    order.save(update_fields=['status', 'updated_at'])
    return order

@transaction.atomic
def create_sales_order(user, items_data: list, title: str = None, order_date=None) -> SalesOrder:
    """
    Creates a new SalesOrder in DRAFT status.
    items_data: [{'product_id': int, 'quantity': float, 'unit_price': float}]
    """
    if not items_data:
        raise ValidationError("A sales order must have at least one item.")

    _validate_products_belong_to_user(user, items_data)

    order = SalesOrder.objects.create(
        user=user,
        title=title,
        status=OrderStatus.DRAFT,
        **( {'order_date': order_date} if order_date else {} )
    )
    
    for item in items_data:
        SalesOrderItem.objects.create(
            order=order,
            product_id=item['product_id'],
            quantity=item['quantity'],
            unit_price=item['unit_price']
        )
    return order

@transaction.atomic
def confirm_sales_order(
    order: SalesOrder,
    *,
    allocation_strategy: str = StockAllocationStrategy.FIFO,
) -> SalesOrder:
    """
    Transitions SO to CONFIRMED.
    Deducts stock using FIFO (created_at) or hybrid FEFO (best_before, then created_at).
    Raises ValidationError if insufficient stock.
    """
    if allocation_strategy not in StockAllocationStrategy.values:
        raise ValidationError('Invalid allocation strategy.')

    if order.status != OrderStatus.DRAFT:
        raise ValidationError(ORDER_NOT_DRAFT)

    for item in order.items.select_related('product').all():
        remaining_to_deduct = Decimal(str(item.quantity))

        available_batches = list(
            available_batches_for_allocation(
                user=order.user,
                product=item.product,
                strategy=allocation_strategy,
            ).select_for_update()
        )

        total_available = sum(batch.current_quantity for batch in available_batches)
        if total_available < remaining_to_deduct:
            raise ValidationError(f"Insufficient stock for {item.product.name}. Required: {remaining_to_deduct}, Available: {total_available}")

        for batch in available_batches:
            if remaining_to_deduct <= 0:
                break
            
            deduct_amount = min(batch.current_quantity, remaining_to_deduct)
            record_movement(
                user=order.user,
                stock_batch=batch,
                delta=-deduct_amount,
                reason=MovementReason.SALE,
                sales_order_item=item,
            )
            remaining_to_deduct -= deduct_amount

    order.status = OrderStatus.CONFIRMED
    order.save(update_fields=['status', 'updated_at'])
    return order

@transaction.atomic
def cancel_sales_order(order: SalesOrder) -> SalesOrder:
    """
    Transitions SO to CANCELLED.
    If CONFIRMED, reverses each SALE movement with a matching RETURN on the original batch.
    """
    if order.status == OrderStatus.CANCELLED:
        raise ValidationError(ORDER_ALREADY_CANCELLED)

    if order.status == OrderStatus.CONFIRMED:
        sale_movements = list(
            StockMovement.objects.filter(
                user=order.user,
                sales_order_item__order=order,
                reason=MovementReason.SALE,
            ).select_related('stock_batch', 'sales_order_item')
        )

        if not sale_movements:
            # Edge case: status is CONFIRMED but confirm_sales_order never ran (e.g. manual
            # DB edit). Normal confirms always create SALE movements; cancel needs those to
            # restore stock, so we block rather than silently mark cancelled.
            raise ValidationError(ORDER_CANCEL_UNAVAILABLE)

        batch_ids = {m.stock_batch_id for m in sale_movements}
        list(Stock.objects.filter(id__in=batch_ids).select_for_update())

        for movement in sale_movements:
            batch = Stock.objects.get(pk=movement.stock_batch_id)
            record_movement(
                user=order.user,
                stock_batch=batch,
                delta=-movement.delta,
                reason=MovementReason.RETURN,
                sales_order_item=movement.sales_order_item,
            )

    order.status = OrderStatus.CANCELLED
    order.save(update_fields=['status', 'updated_at'])
    return order
