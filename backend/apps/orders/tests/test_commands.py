import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.accounts.models import User
from apps.inventory.models import Product, Stock, MovementReason, StockMovement
from apps.orders.models import OrderStatus, PurchaseOrder, SalesOrder, SalesOrderItem
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
        
        # Cancel untouched
        cancel_purchase_order(po)
        po.refresh_from_db()
        assert po.status == OrderStatus.CANCELLED
        assert Stock.objects.count() == 0
        
    def test_cannot_cancel_consumed_purchase_order(self, user, product):
        items_data = [{'product_id': product.id, 'quantity': 100, 'unit_cost': 10.50}]
        po = create_purchase_order(user, items_data)
        confirm_purchase_order(po)
        
        # Simulate consumption
        stock = Stock.objects.first()
        stock.current_quantity -= Decimal('10')
        stock.save()
        
        with pytest.raises(ValidationError, match="consumed or sold"):
            cancel_purchase_order(po)

@pytest.mark.django_db
class TestSalesOrders:
    def test_fifo_stock_deduction(self, user, product):
        # Create two stock batches: older and newer
        Stock.objects.create(user=user, product=product, initial_quantity=10, current_quantity=10, unit_cost=5.00)
        Stock.objects.create(user=user, product=product, initial_quantity=20, current_quantity=20, unit_cost=6.00)
        
        items_data = [{'product_id': product.id, 'quantity': 15, 'unit_price': 15.00}]
        so = create_sales_order(user, items_data)
        
        confirm_sales_order(so)
        
        # FIFO check
        stocks = Stock.objects.order_by('created_at')
        assert stocks[0].current_quantity == Decimal('0.000')   # First batch fully consumed
        assert stocks[1].current_quantity == Decimal('15.000')  # Second batch partially consumed

    def test_insufficient_stock(self, user, product):
        Stock.objects.create(user=user, product=product, initial_quantity=10, current_quantity=10, unit_cost=5.00)
        
        items_data = [{'product_id': product.id, 'quantity': 15, 'unit_price': 15.00}]
        so = create_sales_order(user, items_data)
        
        with pytest.raises(ValidationError, match="Insufficient stock"):
            confirm_sales_order(so)
            
        # Verify transaction rolled back, stock untouched
        stock = Stock.objects.first()
        assert stock.current_quantity == Decimal('10.000')

    def test_cancel_sales_order_refunds_stock(self, user, product):
        Stock.objects.create(user=user, product=product, initial_quantity=20, current_quantity=20, unit_cost=5.00)
        items_data = [{'product_id': product.id, 'quantity': 15, 'unit_price': 15.00}]
        so = create_sales_order(user, items_data)
        confirm_sales_order(so)
        
        stock = Stock.objects.first()
        assert stock.current_quantity == Decimal('5.000')
        
        # Cancel
        cancel_sales_order(so)
        so.refresh_from_db()
        assert so.status == OrderStatus.CANCELLED
        
        stock.refresh_from_db()
        # Refund adds back the 15 to current_quantity, AND bumps initial_quantity so it's not locked.
        assert stock.current_quantity == Decimal('20.000')
        assert stock.initial_quantity == Decimal('35.000')

    def test_cannot_create_sales_order_with_another_users_product(self, user, product):
        other_user = User.objects.create_user(
            username="other@example.com", email="other@example.com", password="password"
        )
        items_data = [{'product_id': product.id, 'quantity': 10, 'unit_price': 15.00}]

        with pytest.raises(ValidationError, match="do not belong"):
            create_sales_order(other_user, items_data)

    def test_cannot_drain_another_users_stock_on_confirm(self, user, product):
        """Even if line items were inserted directly, confirm only deducts the order owner's stock."""
        attacker = User.objects.create_user(
            username="attacker@example.com", email="attacker@example.com", password="password"
        )
        victim_product = Product.objects.create(
            user=user, name="Victim Tea", sku="VIC-1", unit_of_measure="UNIT"
        )
        victim_stock = Stock.objects.create(
            user=user,
            product=victim_product,
            initial_quantity=100,
            current_quantity=100,
            unit_cost=5.00,
        )

        so = SalesOrder.objects.create(user=attacker, status=OrderStatus.DRAFT)
        SalesOrderItem.objects.create(
            order=so, product=victim_product, quantity=50, unit_price=20.00
        )

        with pytest.raises(ValidationError, match="Insufficient stock"):
            confirm_sales_order(so)

        victim_stock.refresh_from_db()
        assert victim_stock.current_quantity == Decimal('100.000')
