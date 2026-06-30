from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from apps.orders.models import PurchaseOrder, PurchaseOrderItem, SalesOrder, SalesOrderItem, OrderStatus
from apps.inventory.models import Product, Stock, MovementReason, StockMovement
from apps.inventory.commands import record_movement


def _validate_products_belong_to_user(user, items_data: list) -> None:
    """Ensure every product_id in the order belongs to the requesting user."""
    product_ids = {item['product_id'] for item in items_data}
    owned_ids = set(
        Product.objects.filter(user=user, id__in=product_ids).values_list('id', flat=True)
    )
    if owned_ids != product_ids:
        raise ValidationError("One or more products do not belong to your account.")

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
        raise ValidationError("Only DRAFT purchase orders can be confirmed.")

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
    If CONFIRMED, it attempts to delete the generated Stock batches.
    If any Stock batch has been partially or fully consumed, it raises an error.
    """
    if order.status == OrderStatus.CANCELLED:
        raise ValidationError("Order is already cancelled.")

    if order.status == OrderStatus.CONFIRMED:
        # Fetch all stock batches created by this order
        stock_batches = Stock.objects.filter(purchase_order_item__order=order)
        
        for batch in stock_batches:
            if batch.current_quantity < batch.initial_quantity:
                raise ValidationError("Cannot cancel a confirmed order because some of the received stock has already been consumed or sold.")
        
        # If untouched, safely delete the physical stock
        stock_batches.delete()

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
def confirm_sales_order(order: SalesOrder) -> SalesOrder:
    """
    Transitions SO to CONFIRMED.
    Implements FIFO stock deduction: deducts stock from the oldest available batches.
    Raises ValidationError if insufficient stock.
    """
    if order.status != OrderStatus.DRAFT:
        raise ValidationError("Only DRAFT sales orders can be confirmed.")

    for item in order.items.select_related('product').all():
        remaining_to_deduct = Decimal(str(item.quantity))
        
        # Lock the stock rows to prevent race conditions during FIFO allocation
        available_batches = list(Stock.objects.filter(
            user=order.user,
            product=item.product,
            current_quantity__gt=0
        ).order_by('created_at').select_for_update())

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
        raise ValidationError("Order is already cancelled.")

    if order.status == OrderStatus.CONFIRMED:
        sale_movements = list(
            StockMovement.objects.filter(
                user=order.user,
                sales_order_item__order=order,
                reason=MovementReason.SALE,
            ).select_related('stock_batch', 'sales_order_item')
        )

        if not sale_movements:
            raise ValidationError("Cannot cancel: no stock movements found for this order.")

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
