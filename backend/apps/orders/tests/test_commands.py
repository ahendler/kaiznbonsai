import pytest
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.models import Sum
from apps.accounts.models import User
from apps.inventory.models import Product, Stock, MovementReason, StockMovement
from apps.orders.models import OrderStatus, PurchaseOrder, SalesOrder, SalesOrderItem
from apps.inventory.commands import record_movement
from apps.orders.constants import StockAllocationStrategy
from apps.orders.commands import (
    create_purchase_order,
    confirm_purchase_order,
    cancel_purchase_order,
    create_sales_order,
    confirm_sales_order,
    cancel_sales_order
)

@pytest.fixture
def user():
    return User.objects.create_user(username="test@example.com", email="test@example.com", password="password")

@pytest.fixture
def product(user):
    return Product.objects.create(
        user=user,
        name="Matcha",
        sku="MATCHA-1",
        unit_of_measure="UNIT"
    )


def make_stock_with_receipt(user, product, quantity, unit_cost=Decimal('5.00'), best_before=None):
    stock = Stock.objects.create(
        user=user,
        product=product,
        initial_quantity=Decimal(str(quantity)),
        current_quantity=Decimal('0'),
        unit_cost=unit_cost,
        best_before=best_before,
    )
    record_movement(
        user=user,
        stock_batch=stock,
        delta=Decimal(str(quantity)),
        reason=MovementReason.RECEIPT,
    )
    stock.refresh_from_db()
    return stock

@pytest.mark.django_db
class TestPurchaseOrders:
    def test_create_and_confirm_purchase_order(self, user, product):
        items_data = [
            {'product_id': product.id, 'quantity': 100, 'unit_cost': 10.50, 'lot_code': 'LOT1', 'best_before': None}
        ]
        
        # Create
        po = create_purchase_order(user, items_data)
        assert po.status == OrderStatus.DRAFT
        assert po.items.count() == 1
        assert Stock.objects.count() == 0
        
        # Confirm
        confirm_purchase_order(po)
        po.refresh_from_db()
        assert po.status == OrderStatus.CONFIRMED
        
        assert Stock.objects.count() == 1
        stock = Stock.objects.first()
        assert stock.initial_quantity == Decimal('100.000')
        assert stock.current_quantity == Decimal('100.000')
        assert stock.unit_cost == Decimal('10.50')
        assert stock.lot_code == 'LOT1'
        assert stock.movements.filter(reason=MovementReason.RECEIPT).count() == 1

    def test_cancel_confirmed_purchase_order(self, user, product):
        items_data = [{'product_id': product.id, 'quantity': 100, 'unit_cost': 10.50}]
        po = create_purchase_order(user, items_data)
        confirm_purchase_order(po)

        cancel_purchase_order(po)
        po.refresh_from_db()
        assert po.status == OrderStatus.CANCELLED

        stock = Stock.objects.get(purchase_order_item__order=po)
        assert stock.voided_at is not None
        assert stock.current_quantity == Decimal('0')
        assert stock.movements.filter(reason=MovementReason.RECEIPT).count() == 1
        assert stock.movements.filter(reason=MovementReason.RECEIPT_REVERSAL).count() == 1
        
    def test_cannot_cancel_consumed_purchase_order(self, user, product):
        items_data = [{'product_id': product.id, 'quantity': 100, 'unit_cost': 10.50}]
        po = create_purchase_order(user, items_data)
        confirm_purchase_order(po)

        so = create_sales_order(
            user,
            [{'product_id': product.id, 'quantity': 10, 'unit_price': 15.00}],
        )
        confirm_sales_order(so)

        with pytest.raises(ValidationError, match="used in a sale"):
            cancel_purchase_order(po)

    def test_cannot_cancel_purchase_order_after_sale_and_cancel(self, user, product):
        items_data = [{'product_id': product.id, 'quantity': 100, 'unit_cost': 10.50}]
        po = create_purchase_order(user, items_data)
        confirm_purchase_order(po)
        stock = Stock.objects.get(purchase_order_item__order=po)

        so = create_sales_order(
            user,
            [{'product_id': product.id, 'quantity': 10, 'unit_price': 15.00}],
        )
        confirm_sales_order(so)
        cancel_sales_order(so)

        stock.refresh_from_db()
        assert stock.current_quantity == stock.initial_quantity

        with pytest.raises(ValidationError, match="used in a sale"):
            cancel_purchase_order(po)

        po.refresh_from_db()
        assert po.status == OrderStatus.CONFIRMED
        assert Stock.objects.filter(id=stock.id).exists()

@pytest.mark.django_db
class TestSalesOrders:
    def test_single_batch_sale_creates_sale_movement(self, user, product):
        stock = make_stock_with_receipt(user, product, 20)
        items_data = [{'product_id': product.id, 'quantity': 15, 'unit_price': 15.00}]
        so = create_sales_order(user, items_data)
        item = so.items.get()

        confirm_sales_order(so)

        stock.refresh_from_db()
        assert stock.current_quantity == Decimal('5.000')

        sale = stock.movements.get(reason=MovementReason.SALE)
        assert sale.delta == Decimal('-15.000')
        assert sale.sales_order_item_id == item.id

        total_delta = stock.movements.aggregate(total=Sum('delta'))['total']
        assert total_delta == stock.current_quantity

    def test_fifo_stock_deduction(self, user, product):
        make_stock_with_receipt(user, product, 10, unit_cost=Decimal('5.00'))
        make_stock_with_receipt(user, product, 20, unit_cost=Decimal('6.00'))

        items_data = [{'product_id': product.id, 'quantity': 15, 'unit_price': 15.00}]
        so = create_sales_order(user, items_data)
        item = so.items.get()

        confirm_sales_order(so)

        stocks = Stock.objects.order_by('created_at')
        assert stocks[0].current_quantity == Decimal('0.000')
        assert stocks[1].current_quantity == Decimal('15.000')

        sale_movements = StockMovement.objects.filter(
            reason=MovementReason.SALE,
            sales_order_item=item,
        ).order_by('created_at')
        assert sale_movements.count() == 2
        assert sale_movements[0].delta == Decimal('-10.000')
        assert sale_movements[1].delta == Decimal('-5.000')
        assert sum(m.delta for m in sale_movements) == Decimal('-15.000')

        for stock in stocks:
            total_delta = stock.movements.aggregate(total=Sum('delta'))['total']
            assert total_delta == stock.current_quantity

    def test_confirm_default_fifo_matches_explicit_fifo(self, user, product):
        make_stock_with_receipt(user, product, 10)
        make_stock_with_receipt(user, product, 20)
        so = create_sales_order(
            user,
            [{'product_id': product.id, 'quantity': 5, 'unit_price': 10.00}],
        )

        confirm_sales_order(so)

        stocks = list(Stock.objects.order_by('created_at'))
        assert stocks[0].current_quantity == Decimal('5.000')
        assert stocks[1].current_quantity == Decimal('20.000')

    def test_confirm_fefo_prefers_earlier_best_before(self, user, product):
        later = make_stock_with_receipt(user, product, 10, best_before=date(2026, 12, 31))
        sooner = make_stock_with_receipt(user, product, 10, best_before=date(2026, 6, 1))
        so = create_sales_order(
            user,
            [{'product_id': product.id, 'quantity': 5, 'unit_price': 10.00}],
        )

        confirm_sales_order(so, allocation_strategy=StockAllocationStrategy.FEFO)

        sooner.refresh_from_db()
        later.refresh_from_db()
        assert sooner.current_quantity == Decimal('5.000')
        assert later.current_quantity == Decimal('10.000')

    def test_confirm_fefo_dated_before_undated(self, user, product):
        undated = make_stock_with_receipt(user, product, 10, best_before=None)
        dated = make_stock_with_receipt(user, product, 10, best_before=date(2026, 6, 1))
        so = create_sales_order(
            user,
            [{'product_id': product.id, 'quantity': 5, 'unit_price': 10.00}],
        )

        confirm_sales_order(so, allocation_strategy=StockAllocationStrategy.FEFO)

        undated.refresh_from_db()
        dated.refresh_from_db()
        assert dated.current_quantity == Decimal('5.000')
        assert undated.current_quantity == Decimal('10.000')

    def test_confirm_fefo_same_best_before_uses_fifo_tiebreak(self, user, product):
        same_date = date(2026, 6, 1)
        older = make_stock_with_receipt(user, product, 10, best_before=same_date)
        newer = make_stock_with_receipt(user, product, 10, best_before=same_date)
        assert older.created_at < newer.created_at
        so = create_sales_order(
            user,
            [{'product_id': product.id, 'quantity': 5, 'unit_price': 10.00}],
        )

        confirm_sales_order(so, allocation_strategy=StockAllocationStrategy.FEFO)

        older.refresh_from_db()
        newer.refresh_from_db()
        assert older.current_quantity == Decimal('5.000')
        assert newer.current_quantity == Decimal('10.000')

    def test_confirm_fefo_all_undated_matches_fifo(self, user, product):
        make_stock_with_receipt(user, product, 10)
        make_stock_with_receipt(user, product, 20)
        so = create_sales_order(
            user,
            [{'product_id': product.id, 'quantity': 15, 'unit_price': 10.00}],
        )

        confirm_sales_order(so, allocation_strategy=StockAllocationStrategy.FEFO)

        stocks = list(Stock.objects.order_by('created_at'))
        assert stocks[0].current_quantity == Decimal('0.000')
        assert stocks[1].current_quantity == Decimal('15.000')

    def test_confirm_invalid_allocation_strategy(self, user, product):
        make_stock_with_receipt(user, product, 10)
        so = create_sales_order(
            user,
            [{'product_id': product.id, 'quantity': 5, 'unit_price': 10.00}],
        )

        with pytest.raises(ValidationError, match="Invalid allocation"):
            confirm_sales_order(so, allocation_strategy='BAD')

    def test_insufficient_stock(self, user, product):
        make_stock_with_receipt(user, product, 10)

        items_data = [{'product_id': product.id, 'quantity': 15, 'unit_price': 15.00}]
        so = create_sales_order(user, items_data)

        with pytest.raises(ValidationError, match="Insufficient stock"):
            confirm_sales_order(so)

        stock = Stock.objects.first()
        assert stock.current_quantity == Decimal('10.000')
        assert StockMovement.objects.filter(reason=MovementReason.SALE).count() == 0

    def test_cancel_sales_order_refunds_stock(self, user, product):
        stock = make_stock_with_receipt(user, product, 20)
        items_data = [{'product_id': product.id, 'quantity': 15, 'unit_price': 15.00}]
        so = create_sales_order(user, items_data)
        confirm_sales_order(so)

        stock.refresh_from_db()
        assert stock.current_quantity == Decimal('5.000')

        cancel_sales_order(so)
        so.refresh_from_db()
        assert so.status == OrderStatus.CANCELLED

        stock.refresh_from_db()
        assert stock.current_quantity == Decimal('20.000')
        assert stock.initial_quantity == Decimal('20.000')

        return_movement = stock.movements.get(reason=MovementReason.RETURN)
        assert return_movement.delta == Decimal('15.000')
        total_delta = stock.movements.aggregate(total=Sum('delta'))['total']
        assert total_delta == stock.current_quantity

    def test_multi_batch_fifo_sale_then_cancel_restores_batches(self, user, product):
        batch_a = make_stock_with_receipt(user, product, 10, unit_cost=Decimal('5.00'))
        batch_b = make_stock_with_receipt(user, product, 20, unit_cost=Decimal('6.00'))

        items_data = [{'product_id': product.id, 'quantity': 15, 'unit_price': 15.00}]
        so = create_sales_order(user, items_data)
        confirm_sales_order(so)

        batch_a.refresh_from_db()
        batch_b.refresh_from_db()
        assert batch_a.current_quantity == Decimal('0.000')
        assert batch_b.current_quantity == Decimal('15.000')

        cancel_sales_order(so)

        batch_a.refresh_from_db()
        batch_b.refresh_from_db()
        assert batch_a.current_quantity == Decimal('10.000')
        assert batch_b.current_quantity == Decimal('20.000')

        sale_movements = StockMovement.objects.filter(
            sales_order_item__order=so,
            reason=MovementReason.SALE,
        )
        return_movements = StockMovement.objects.filter(
            sales_order_item__order=so,
            reason=MovementReason.RETURN,
        )
        assert sale_movements.count() == 2
        assert return_movements.count() == 2

        for sale in sale_movements:
            matching_return = return_movements.get(
                stock_batch_id=sale.stock_batch_id,
                sales_order_item_id=sale.sales_order_item_id,
            )
            assert matching_return.delta == -sale.delta

    def test_cancel_draft_order_creates_no_movements(self, user, product):
        make_stock_with_receipt(user, product, 10)
        items_data = [{'product_id': product.id, 'quantity': 5, 'unit_price': 15.00}]
        so = create_sales_order(user, items_data)

        cancel_sales_order(so)

        so.refresh_from_db()
        assert so.status == OrderStatus.CANCELLED
        assert StockMovement.objects.filter(reason=MovementReason.RETURN).count() == 0
        assert StockMovement.objects.filter(reason=MovementReason.SALE).count() == 0

    def test_cancel_confirmed_without_sale_movements_raises(self, user, product):
        so = create_sales_order(
            user,
            [{'product_id': product.id, 'quantity': 5, 'unit_price': 15.00}],
        )
        so.status = OrderStatus.CONFIRMED
        so.save(update_fields=['status', 'updated_at'])

        with pytest.raises(ValidationError, match="no stock was deducted"):
            cancel_sales_order(so)

        so.refresh_from_db()
        assert so.status == OrderStatus.CONFIRMED

    def test_cannot_create_sales_order_with_another_users_product(self, user, product):
        other_user = User.objects.create_user(
            username="other@example.com", email="other@example.com", password="password"
        )
        items_data = [{'product_id': product.id, 'quantity': 10, 'unit_price': 15.00}]

        with pytest.raises(ValidationError, match="not found"):
            create_sales_order(other_user, items_data)

    def test_cannot_drain_another_users_stock_on_confirm(self, user, product):
        """Even if line items were inserted directly, confirm only deducts the order owner's stock."""
        attacker = User.objects.create_user(
            username="attacker@example.com", email="attacker@example.com", password="password"
        )
        victim_product = Product.objects.create(
            user=user, name="Victim Tea", sku="VIC-1", unit_of_measure="UNIT"
        )
        victim_stock = make_stock_with_receipt(user, victim_product, 100, unit_cost=Decimal('5.00'))

        so = SalesOrder.objects.create(user=attacker, status=OrderStatus.DRAFT)
        SalesOrderItem.objects.create(
            order=so, product=victim_product, quantity=50, unit_price=20.00
        )

        with pytest.raises(ValidationError, match="Insufficient stock"):
            confirm_sales_order(so)

        victim_stock.refresh_from_db()
        assert victim_stock.current_quantity == Decimal('100.000')
