"""
Unit tests for apps.assistant.tools — executor functions and dispatcher.

No Anthropic API key or network access required. All tests call execute_tool
directly against the database.

Coverage focus: logic that lives only in the tool layer — computed fields
(inventory_value, total_cost, total_revenue), executor-only params (in_stock,
limit), serialisation contracts (Decimal → str, date → ISO string), output
shape for new data structures (items lists, order references), and the
dispatcher itself.

Selector-level filtering logic (margin bands, movement reasons, date ranges)
is already exercised in test_financials.py and test_activity.py.
"""
import pytest
from datetime import date
from decimal import Decimal

from apps.accounts.models import User
from apps.inventory.commands import record_movement
from apps.inventory.models import MovementReason, Product, Stock
from apps.orders.commands import (
    confirm_purchase_order,
    confirm_sales_order,
    create_purchase_order,
    create_sales_order,
)
from apps.assistant.tools import execute_tool


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_a(db):
    return User.objects.create_user(
        username='assistant_user_a', email='a@assistant.test', password='PassA123!'
    )


@pytest.fixture
def user_b(db):
    return User.objects.create_user(
        username='assistant_user_b', email='b@assistant.test', password='PassB123!'
    )


@pytest.fixture
def product_a(user_a):
    return Product.objects.create(
        user=user_a, name='Oat Milk', sku='OAT-01', unit_of_measure='L',
    )


@pytest.fixture
def product_b(user_a):
    return Product.objects.create(
        user=user_a, name='Cold Brew', sku='CB-02', unit_of_measure='L',
    )


@pytest.fixture
def stock_a(user_a, product_a):
    """100 L in stock at $2.50/unit. Start at 0 so record_movement lands at 100."""
    batch = Stock.objects.create(
        user=user_a,
        product=product_a,
        initial_quantity=Decimal('100'),
        current_quantity=Decimal('0'),
        unit_cost=Decimal('2.50'),
        lot_code='LOT-A1',
        best_before=date(2027, 6, 1),
    )
    record_movement(user=user_a, stock_batch=batch, delta=Decimal('100'), reason=MovementReason.RECEIPT)
    batch.refresh_from_db()
    return batch


@pytest.fixture
def stock_b(user_a, product_b):
    """Depleted batch (current_quantity == 0)."""
    return Stock.objects.create(
        user=user_a,
        product=product_b,
        initial_quantity=Decimal('50'),
        current_quantity=Decimal('0'),
        unit_cost=Decimal('5.00'),
        lot_code='LOT-B1',
    )


@pytest.fixture
def confirmed_sale(user_a, product_a, stock_a):
    """Confirmed SO: 10 L of Oat Milk at $4.00/unit."""
    so = create_sales_order(
        user_a,
        [{'product_id': product_a.id, 'quantity': 10, 'unit_price': 4.00}],
        title='SO-001',
    )
    confirm_sales_order(so, allocation_strategy='FIFO')
    so.refresh_from_db()
    return so


@pytest.fixture
def confirmed_po(user_a, product_a):
    """Confirmed PO: 20 units of Oat Milk at $2.00/unit."""
    po = create_purchase_order(
        user_a,
        [{'product_id': product_a.id, 'quantity': 20, 'unit_cost': 2.00, 'lot_code': 'PO-LOT'}],
        title='PO-001',
    )
    confirm_purchase_order(po)
    po.refresh_from_db()
    return po


@pytest.fixture
def product_other(user_b):
    return Product.objects.create(
        user=user_b, name='Other Product', sku='OTH-01', unit_of_measure='KG',
    )


# ---------------------------------------------------------------------------
# get_overall_financials
# ---------------------------------------------------------------------------

class TestGetOverallFinancials:
    def test_output_contract(self, user_a):
        """Keys are correct, all values are JSON-safe strings, zeros when no data."""
        result = execute_tool('get_overall_financials', {}, user=user_a)
        assert set(result.keys()) == {'revenue', 'cogs', 'gross_profit', 'margin', 'inventory_value'}
        for key, val in result.items():
            assert isinstance(val, str), f"{key!r} should be a string, got {type(val)}"
        assert Decimal(result['revenue']) == Decimal('0.00')
        assert Decimal(result['cogs']) == Decimal('0.00')


# ---------------------------------------------------------------------------
# get_products_with_financials
# ---------------------------------------------------------------------------

class TestGetProductsWithFinancials:
    def test_output_contract(self, user_a, product_a, stock_a):
        """Keys and Decimal → str serialisation."""
        result = execute_tool('get_products_with_financials', {}, user=user_a)
        assert isinstance(result, list) and len(result) >= 1
        row = next(r for r in result if r['sku'] == 'OAT-01')
        assert {'id', 'name', 'sku', 'unit_of_measure', 'revenue', 'cogs', 'profit',
                'margin', 'markup_on_cost', 'qty_sold', 'qty_purchased'} <= set(row.keys())
        for field in ('revenue', 'cogs', 'profit', 'margin', 'qty_sold', 'qty_purchased'):
            assert isinstance(row[field], str), f"{field!r} should be a string"

    def test_limit_respected(self, user_a, product_a, product_b, stock_a, stock_b):
        """limit is sliced in the executor, not in the selector."""
        result = execute_tool('get_products_with_financials', {'limit': 1}, user=user_a)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# get_stock_levels
# ---------------------------------------------------------------------------

class TestGetStockLevels:
    def test_row_shape_and_computed_fields(self, user_a, stock_a):
        """Keys, inventory_value (current_qty × unit_cost), and date serialisation."""
        result = execute_tool('get_stock_levels', {'product_id': str(stock_a.product_id)}, user=user_a)
        assert len(result) == 1
        row = result[0]
        assert {'id', 'product_name', 'product_sku', 'unit_of_measure', 'lot_code',
                'best_before', 'initial_quantity', 'current_quantity',
                'unit_cost', 'inventory_value'} <= set(row.keys())
        assert Decimal(row['inventory_value']) == Decimal('250.00')  # 100 L × $2.50
        assert row['best_before'] == '2027-06-01'

    def test_filters(self, user_a, product_a, stock_a, stock_b):
        """product_id narrows to one product; in_stock excludes depleted batches."""
        by_product = execute_tool('get_stock_levels', {'product_id': str(product_a.id)}, user=user_a)
        assert all(r['product_sku'] == 'OAT-01' for r in by_product)
        assert str(stock_b.id) not in [r['id'] for r in by_product]

        in_stock = execute_tool('get_stock_levels', {'in_stock': True}, user=user_a)
        ids = [r['id'] for r in in_stock]
        assert str(stock_a.id) in ids
        assert str(stock_b.id) not in ids  # current_quantity == 0

    def test_does_not_return_other_users_batches(self, user_a, user_b, stock_a, product_other):
        Stock.objects.create(
            user=user_b, product=product_other,
            initial_quantity=Decimal('10'), current_quantity=Decimal('10'), unit_cost=Decimal('1.00'),
        )
        result = execute_tool('get_stock_levels', {}, user=user_a)
        assert 'OTH-01' not in [r['product_sku'] for r in result]


# ---------------------------------------------------------------------------
# list_purchase_orders
# ---------------------------------------------------------------------------

class TestListPurchaseOrders:
    def test_row_shape_and_computed_fields(self, user_a, confirmed_po):
        """Items list is populated; total_cost is calculated in the executor."""
        result = execute_tool('list_purchase_orders', {}, user=user_a)
        po_row = next(r for r in result if r['title'] == 'PO-001')
        assert len(po_row['items']) == 1
        item = po_row['items'][0]
        assert item['product_sku'] == 'OAT-01'
        assert Decimal(item['quantity']) == Decimal('20')
        assert Decimal(item['unit_cost']) == Decimal('2.00')
        assert Decimal(po_row['total_cost']) == Decimal('40.00')  # 20 × $2.00


# ---------------------------------------------------------------------------
# list_sales_orders
# ---------------------------------------------------------------------------

class TestListSalesOrders:
    def test_row_shape_and_computed_fields(self, user_a, stock_a, confirmed_sale):
        """Items list is populated; total_revenue is calculated in the executor."""
        result = execute_tool('list_sales_orders', {}, user=user_a)
        so_row = next(r for r in result if r['title'] == 'SO-001')
        assert len(so_row['items']) == 1
        item = so_row['items'][0]
        assert item['product_sku'] == 'OAT-01'
        assert Decimal(item['quantity']) == Decimal('10')
        assert Decimal(item['unit_price']) == Decimal('4.00')
        assert Decimal(so_row['total_revenue']) == Decimal('40.00')  # 10 × $4.00


# ---------------------------------------------------------------------------
# list_stock_movements
# ---------------------------------------------------------------------------

class TestListStockMovements:
    def test_row_shape_and_order_references(self, user_a, stock_a, confirmed_sale):
        """Keys are correct; SALE rows carry a sales_order object, not null."""
        result = execute_tool('list_stock_movements', {'reasons': ['SALE']}, user=user_a)
        assert len(result) >= 1
        row = result[0]
        assert {'id', 'created_at', 'reason', 'delta', 'product_name',
                'product_sku', 'unit_of_measure', 'lot_code',
                'sales_order', 'purchase_order'} <= set(row.keys())
        assert row['sales_order'] is not None
        assert row['sales_order']['title'] == 'SO-001'
        assert row['purchase_order'] is None

    def test_limit_respected(self, user_a, stock_a, confirmed_sale):
        """limit is sliced in the executor, not in the selector."""
        result = execute_tool('list_stock_movements', {'limit': 1}, user=user_a)
        assert len(result) == 1

    def test_does_not_return_other_users_movements(self, user_a, user_b, stock_a, product_other):
        other_stock = Stock.objects.create(
            user=user_b, product=product_other,
            initial_quantity=Decimal('5'), current_quantity=Decimal('5'), unit_cost=Decimal('1.00'),
        )
        record_movement(user=user_b, stock_batch=other_stock, delta=Decimal('5'), reason=MovementReason.RECEIPT)
        result = execute_tool('list_stock_movements', {}, user=user_a)
        assert 'OTH-01' not in [r['product_sku'] for r in result]


# ---------------------------------------------------------------------------
# Dispatcher — execute_tool
# ---------------------------------------------------------------------------

class TestExecuteTool:
    def test_raises_for_unknown_tool(self, user_a):
        with pytest.raises(ValueError, match='Unknown tool'):
            execute_tool('nonexistent_tool', {}, user=user_a)
