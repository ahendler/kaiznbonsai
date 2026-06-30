"""Tests for inventory Product and Stock endpoints.

Coverage:
- Tenant isolation: User A cannot access or modify User B's data.
- Ownership injection: products and stocks are always owned by the requesting user.
- total_stock aggregation: correct sum across multiple batches.
- SKU uniqueness constraint is enforced per user, not globally.
- Product deletion guard: 409 Conflict when active stock batches exist.
- Stock cross-user creation guard: cannot add stock to another user's product.
"""
import pytest
from decimal import Decimal
from django.db.models import Sum
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.inventory.commands import record_movement
from apps.inventory.models import MovementReason, Product, Stock, StockMovement
from apps.orders.commands import (
    cancel_sales_order,
    confirm_sales_order,
    create_sales_order,
)

PRODUCTS_URL = '/api/v1/inventory/products/'
STOCKS_URL = '/api/v1/inventory/stocks/'


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_a(db):
    return User.objects.create_user(
        username='user_a', email='a@example.com', password='PassA123!'
    )


@pytest.fixture
def user_b(db):
    return User.objects.create_user(
        username='user_b', email='b@example.com', password='PassB123!'
    )


@pytest.fixture
def client_a(user_a):
    """Authenticated APIClient for User A."""
    client = APIClient()
    r = client.post('/api/v1/auth/login/', {'email': user_a.email, 'password': 'PassA123!'}, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return client


@pytest.fixture
def client_b(user_b):
    """Authenticated APIClient for User B."""
    client = APIClient()
    r = client.post('/api/v1/auth/login/', {'email': user_b.email, 'password': 'PassB123!'}, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return client


@pytest.fixture
def product_a(user_a):
    """A product owned by User A."""
    return Product.objects.create(
        user=user_a, name='Green Tea', sku='GT-001', unit_of_measure='KG'
    )


@pytest.fixture
def product_b(user_b):
    """A product owned by User B."""
    return Product.objects.create(
        user=user_b, name='Black Tea', sku='BT-001', unit_of_measure='KG'
    )


def make_stock(user, product, quantity, cost='10.00', lot='LOT-A'):
    """Helper to create a stock batch with a RECEIPT movement."""
    stock = Stock.objects.create(
        user=user,
        product=product,
        lot_code=lot,
        initial_quantity=Decimal(quantity),
        current_quantity=Decimal('0'),
        unit_cost=Decimal(cost),
    )
    record_movement(
        user=user,
        stock_batch=stock,
        delta=Decimal(quantity),
        reason=MovementReason.RECEIPT,
    )
    stock.refresh_from_db()
    return stock


# ---------------------------------------------------------------------------
# Tenant Isolation: Products
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProductTenantIsolation:
    def test_user_only_sees_own_products(self, client_a, product_a, product_b):
        r = client_a.get(PRODUCTS_URL)
        assert r.status_code == status.HTTP_200_OK
        ids = [p['id'] for p in r.data['results']]
        assert product_a.id in ids
        assert product_b.id not in ids

    def test_user_cannot_retrieve_another_users_product(self, client_a, product_b):
        r = client_a.get(f'{PRODUCTS_URL}{product_b.id}/')
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_user_cannot_update_another_users_product(self, client_a, product_b):
        r = client_a.patch(f'{PRODUCTS_URL}{product_b.id}/', {'name': 'Hacked'}, format='json')
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_user_cannot_delete_another_users_product(self, client_a, product_b):
        r = client_a.delete(f'{PRODUCTS_URL}{product_b.id}/')
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_create_product_injects_request_user_as_owner(self, client_a, user_a):
        payload = {'name': 'Matcha', 'sku': 'MAT-001', 'unit_of_measure': 'KG'}
        r = client_a.post(PRODUCTS_URL, payload, format='json')
        assert r.status_code == status.HTTP_201_CREATED
        assert Product.objects.get(id=r.data['id']).user_id == user_a.id


# ---------------------------------------------------------------------------
# Tenant Isolation: Stocks
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestStockTenantIsolation:
    def test_user_only_sees_own_stock_batches(self, client_a, user_a, user_b, product_a, product_b):
        batch_a = make_stock(user_a, product_a, 100)
        batch_b = make_stock(user_b, product_b, 200)
        r = client_a.get(STOCKS_URL)
        assert r.status_code == status.HTTP_200_OK
        ids = [str(s['id']) for s in r.data['results']]
        assert str(batch_a.id) in ids
        assert str(batch_b.id) not in ids

    def test_user_cannot_add_stock_to_another_users_product(self, client_a, product_b):
        payload = {
            'product': product_b.id,
            'lot_code': 'LOT-X',
            'initial_quantity': '50.000',
            'current_quantity': '50.000',
            'unit_cost': '5.00',
        }
        r = client_a.post(STOCKS_URL, payload, format='json')
        assert r.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# total_stock Aggregation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTotalStockAnnotation:
    def test_total_stock_sums_all_batches(self, client_a, user_a, product_a):
        make_stock(user_a, product_a, '100.000', lot='LOT-1')
        make_stock(user_a, product_a, '50.500', lot='LOT-2')
        r = client_a.get(f'{PRODUCTS_URL}{product_a.id}/')
        assert r.status_code == status.HTTP_200_OK
        assert Decimal(r.data['total_stock']) == Decimal('150.500')

    def test_total_stock_is_zero_when_no_batches(self, client_a, product_a):
        r = client_a.get(f'{PRODUCTS_URL}{product_a.id}/')
        assert r.status_code == status.HTTP_200_OK
        assert Decimal(r.data['total_stock']) == Decimal('0')

    def test_total_stock_only_counts_own_products_batches(self, client_a, user_a, user_b, product_a, product_b):
        make_stock(user_a, product_a, '100.000', lot='LOT-A1')
        make_stock(user_b, product_b, '999.000', lot='LOT-B1')
        r = client_a.get(f'{PRODUCTS_URL}{product_a.id}/')
        assert Decimal(r.data['total_stock']) == Decimal('100.000')


# ---------------------------------------------------------------------------
# SKU Uniqueness Per User
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSkuUniqueness:
    def test_same_sku_for_two_different_users_is_allowed(self, client_a, client_b, user_b):
        payload = {'name': 'Product', 'sku': 'SHARED-SKU', 'unit_of_measure': 'UNIT'}
        r_a = client_a.post(PRODUCTS_URL, payload, format='json')
        r_b = client_b.post(PRODUCTS_URL, payload, format='json')
        assert r_a.status_code == status.HTTP_201_CREATED
        assert r_b.status_code == status.HTTP_201_CREATED

    def test_duplicate_sku_for_same_user_is_rejected(self, client_a, product_a):
        payload = {'name': 'Duplicate', 'sku': product_a.sku, 'unit_of_measure': 'UNIT'}
        r = client_a.post(PRODUCTS_URL, payload, format='json')
        assert r.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Product Deletion Guard
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProductDeletionGuard:
    def test_delete_product_with_stock_returns_409(self, client_a, user_a, product_a):
        make_stock(user_a, product_a, '10.000')
        r = client_a.delete(f'{PRODUCTS_URL}{product_a.id}/')
        assert r.status_code == status.HTTP_409_CONFLICT

    def test_delete_product_without_stock_returns_204(self, client_a, product_a):
        r = client_a.delete(f'{PRODUCTS_URL}{product_a.id}/')
        assert r.status_code == status.HTTP_204_NO_CONTENT
        assert not Product.objects.filter(id=product_a.id).exists()


# ---------------------------------------------------------------------------
# Stock Operations
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestStockOperations:
    def test_create_stock_batch_returns_201(self, client_a, product_a):
        payload = {
            'product': product_a.id,
            'lot_code': 'LOT-001',
            'initial_quantity': '100.000',
            'current_quantity': '999.000',
            'unit_cost': '12.50',
        }
        r = client_a.post(STOCKS_URL, payload, format='json')
        assert r.status_code == status.HTTP_201_CREATED
        assert r.data['lot_code'] == 'LOT-001'
        assert Decimal(r.data['unit_cost']) == Decimal('12.50')
        assert Decimal(r.data['initial_quantity']) == Decimal('100.000')
        assert Decimal(r.data['current_quantity']) == Decimal('100.000')

        batch = Stock.objects.get(id=r.data['id'])
        assert batch.movements.filter(reason=MovementReason.RECEIPT).count() == 1
        total_delta = batch.movements.aggregate(total=Sum('delta'))['total']
        assert total_delta == batch.current_quantity

    def test_create_stock_injects_request_user_as_owner(self, client_a, user_a, product_a):
        payload = {
            'product': product_a.id,
            'lot_code': 'LOT-002',
            'initial_quantity': '50.000',
            'current_quantity': '50.000',
            'unit_cost': '5.00',
        }
        r = client_a.post(STOCKS_URL, payload, format='json')
        assert r.status_code == status.HTTP_201_CREATED
        batch = Stock.objects.get(id=r.data['id'])
        assert batch.user_id == user_a.id

    def test_patch_corrects_current_quantity(self, client_a, user_a, product_a):
        """Covers the data-entry typo correction scenario (e.g. 100 entered instead of 1000)."""
        batch = make_stock(user_a, product_a, '100.000')
        r = client_a.patch(
            f'{STOCKS_URL}{batch.id}/',
            {'current_quantity': '1000.000'},
            format='json'
        )
        assert r.status_code == status.HTTP_200_OK
        batch.refresh_from_db()
        assert batch.current_quantity == Decimal('1000.000')
        assert batch.initial_quantity == Decimal('1000.000')

        adjustment = batch.movements.get(reason=MovementReason.ADJUSTMENT)
        assert adjustment.delta == Decimal('900.000')
        total_delta = batch.movements.aggregate(total=Sum('delta'))['total']
        assert total_delta == batch.current_quantity

    def test_patch_corrects_initial_quantity(self, client_a, user_a, product_a):
        batch = make_stock(user_a, product_a, '100.000')
        r = client_a.patch(
            f'{STOCKS_URL}{batch.id}/',
            {'initial_quantity': '1000.000'},
            format='json'
        )
        assert r.status_code == status.HTTP_200_OK
        batch.refresh_from_db()
        assert batch.current_quantity == Decimal('1000.000')
        assert batch.initial_quantity == Decimal('1000.000')

        adjustment = batch.movements.get(reason=MovementReason.ADJUSTMENT)
        assert adjustment.delta == Decimal('900.000')
        total_delta = batch.movements.aggregate(total=Sum('delta'))['total']
        assert total_delta == batch.current_quantity

    def test_patch_another_users_stock_returns_404(self, client_a, user_b, product_b):
        batch_b = make_stock(user_b, product_b, '200.000')
        r = client_a.patch(
            f'{STOCKS_URL}{batch_b.id}/',
            {'current_quantity': '1.000'},
            format='json'
        )
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_another_users_stock_returns_404(self, client_a, user_b, product_b):
        batch_b = make_stock(user_b, product_b, '200.000')
        r = client_a.delete(f'{STOCKS_URL}{batch_b.id}/')
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_create_stock_with_negative_initial_quantity_returns_400(self, client_a, product_a):
        payload = {
            'product': product_a.id,
            'lot_code': 'LOT-BAD',
            'initial_quantity': '-10.000',
            'current_quantity': '-10.000',
            'unit_cost': '5.00',
        }
        r = client_a.post(STOCKS_URL, payload, format='json')
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_own_stock_returns_204(self, client_a, user_a, product_a):
        """Unconsumed manual batch (RECEIPT only) can be deleted."""
        batch = make_stock(user_a, product_a, '10.000')
        batch_id = batch.id
        assert batch.movements.filter(reason=MovementReason.RECEIPT).count() == 1

        r = client_a.delete(f'{STOCKS_URL}{batch_id}/')
        assert r.status_code == status.HTTP_204_NO_CONTENT
        assert not Stock.objects.filter(id=batch_id).exists()
        assert not StockMovement.objects.filter(stock_batch_id=batch_id).exists()

    def test_delete_partially_sold_batch_returns_409(self, client_a, user_a, product_a):
        batch = make_stock(user_a, product_a, '100.000')
        so = create_sales_order(
            user_a,
            [{'product_id': product_a.id, 'quantity': 10, 'unit_price': 15.00}],
        )
        confirm_sales_order(so)

        r = client_a.delete(f'{STOCKS_URL}{batch.id}/')
        assert r.status_code == status.HTTP_409_CONFLICT
        assert Stock.objects.filter(id=batch.id).exists()

    def test_delete_batch_after_sale_and_cancel_returns_409(self, client_a, user_a, product_a):
        batch = make_stock(user_a, product_a, '100.000')
        so = create_sales_order(
            user_a,
            [{'product_id': product_a.id, 'quantity': 10, 'unit_price': 15.00}],
        )
        confirm_sales_order(so)
        cancel_sales_order(so)

        batch.refresh_from_db()
        assert batch.current_quantity == batch.initial_quantity

        r = client_a.delete(f'{STOCKS_URL}{batch.id}/')
        assert r.status_code == status.HTTP_409_CONFLICT
        assert 'sale' in r.data['detail'].lower()
        assert Stock.objects.filter(id=batch.id).exists()

