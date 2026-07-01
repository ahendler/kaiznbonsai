import pytest
from datetime import date, datetime
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.inventory.commands import record_movement
from apps.inventory.models import MovementReason, Product, Stock, StockMovement
from apps.orders.commands import (
    cancel_sales_order,
    confirm_purchase_order,
    confirm_sales_order,
    create_purchase_order,
    create_sales_order,
)

MOVEMENTS_URL = '/api/v1/inventory/movements/'
STOCKS_URL = '/api/v1/inventory/stocks/'


def _aware(year, month, day):
    return timezone.make_aware(datetime(year, month, day, 12, 0, 0))


def _set_movement_dates(movements, when):
    movements.update(created_at=when)


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
    client = APIClient()
    client.force_authenticate(user=user_a)
    return client


@pytest.fixture
def client_b(user_b):
    client = APIClient()
    client.force_authenticate(user=user_b)
    return client


@pytest.fixture
def product_a(user_a):
    return Product.objects.create(
        user=user_a, name='Oat Milk', sku='DAIR-OAT-01', unit_of_measure='L',
    )


@pytest.fixture
def product_b(user_b):
    return Product.objects.create(
        user=user_b, name='Black Tea', sku='BT-001', unit_of_measure='KG',
    )


@pytest.fixture
def movement_data(user_a, product_a):
    """PO receipt, manual receipt, sale (from PO batch), and manual adjustment."""
    po = create_purchase_order(
        user_a,
        [{'product_id': product_a.id, 'quantity': 50, 'unit_cost': 2.50, 'lot_code': 'PO-LOT'}],
        title='PO-001 — Weekly dairy',
    )
    confirm_purchase_order(po)
    po_stock = Stock.objects.get(purchase_order_item__order=po)
    po_receipt = po_stock.movements.get(reason=MovementReason.RECEIPT)

    manual_stock = Stock.objects.create(
        user=user_a,
        product=product_a,
        lot_code='MANUAL-LOT',
        initial_quantity=Decimal('10'),
        current_quantity=Decimal('0'),
        unit_cost=Decimal('3.00'),
    )
    record_movement(
        user=user_a,
        stock_batch=manual_stock,
        delta=Decimal('10'),
        reason=MovementReason.RECEIPT,
    )

    so = create_sales_order(
        user_a,
        [{'product_id': product_a.id, 'quantity': 5, 'unit_price': 4.00}],
        title='SO-003 — Morning rush',
    )
    confirm_sales_order(so)
    sale = StockMovement.objects.filter(
        reason=MovementReason.SALE,
        sales_order_item__order=so,
    ).first()

    record_movement(
        user=user_a,
        stock_batch=manual_stock,
        delta=Decimal('-1'),
        reason=MovementReason.ADJUSTMENT,
    )

    return {
        'manual_stock': manual_stock,
        'po': po,
        'po_stock': po_stock,
        'po_receipt': po_receipt,
        'so': so,
        'sale': sale,
        'product': product_a,
    }


def _movement_ids(response):
    return [row['id'] for row in response.data['results']]


@pytest.mark.django_db
class TestStockMovementListAPI:
    def test_tenant_isolation(self, client_a, client_b, user_b, movement_data, product_b):
        other_stock = Stock.objects.create(
            user=user_b,
            product=product_b,
            initial_quantity=Decimal('5'),
            current_quantity=Decimal('0'),
            unit_cost=Decimal('1.00'),
        )
        record_movement(
            user=user_b,
            stock_batch=other_stock,
            delta=Decimal('5'),
            reason=MovementReason.RECEIPT,
        )

        res_a = client_a.get(MOVEMENTS_URL)
        res_b = client_b.get(MOVEMENTS_URL)

        assert res_a.status_code == status.HTTP_200_OK
        assert res_b.status_code == status.HTTP_200_OK
        assert len(res_a.data['results']) >= 3
        assert len(res_b.data['results']) == 1

        for row in res_a.data['results']:
            assert row['product']['sku'] == 'DAIR-OAT-01'
        for row in res_b.data['results']:
            assert row['product']['sku'] == 'BT-001'

    def test_default_list_newest_first(self, client_a, movement_data):
        res = client_a.get(MOVEMENTS_URL)
        assert res.status_code == status.HTTP_200_OK
        assert 'next' in res.data
        assert 'previous' in res.data
        assert 'results' in res.data

        created_times = [row['created_at'] for row in res.data['results']]
        assert created_times == sorted(created_times, reverse=True)

    def test_filter_reason_sale(self, client_a, movement_data):
        res = client_a.get(MOVEMENTS_URL, {'reason': 'SALE'})
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data['results']) == 1
        assert res.data['results'][0]['reason'] == 'SALE'
        assert res.data['results'][0]['sales_order']['title'] == 'SO-003 — Morning rush'

    def test_filter_reason_multiple(self, client_a, movement_data):
        res = client_a.get(MOVEMENTS_URL, {'reason': 'RECEIPT,ADJUSTMENT'})
        assert res.status_code == status.HTTP_200_OK
        reasons = {row['reason'] for row in res.data['results']}
        assert reasons == {'RECEIPT', 'ADJUSTMENT'}

    def test_filter_product(self, client_a, movement_data):
        product = movement_data['product']
        res = client_a.get(MOVEMENTS_URL, {'product': product.id})
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data['results']) >= 3
        assert all(row['product']['id'] == product.id for row in res.data['results'])

    def test_filter_stock_batch(self, client_a, movement_data):
        batch = movement_data['manual_stock']
        res = client_a.get(MOVEMENTS_URL, {'stock_batch': str(batch.id)})
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data['results']) == 2
        assert all(row['stock_batch']['id'] == str(batch.id) for row in res.data['results'])

    def test_filter_date_range(self, client_a, movement_data):
        sale = movement_data['sale']
        _set_movement_dates(StockMovement.objects.filter(pk=sale.pk), _aware(2026, 3, 15))
        _set_movement_dates(
            StockMovement.objects.exclude(pk=sale.pk).filter(user=movement_data['product'].user),
            _aware(2026, 2, 1),
        )

        res = client_a.get(
            MOVEMENTS_URL,
            {'from': '2026-03-01', 'to': '2026-03-31'},
        )
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data['results']) == 1
        assert res.data['results'][0]['id'] == str(sale.id)

    def test_date_validation_lone_from(self, client_a, movement_data):
        res = client_a.get(MOVEMENTS_URL, {'from': '2026-03-01'})
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_date_validation_from_after_to(self, client_a, movement_data):
        res = client_a.get(
            MOVEMENTS_URL,
            {'from': '2026-03-31', 'to': '2026-03-01'},
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_search_product_name(self, client_a, movement_data):
        res = client_a.get(MOVEMENTS_URL, {'search': 'Oat'})
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data['results']) >= 3

    def test_search_lot_code(self, client_a, movement_data):
        res = client_a.get(MOVEMENTS_URL, {'search': 'MANUAL-LOT'})
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data['results']) == 2

    def test_search_order_title(self, client_a, movement_data):
        res = client_a.get(MOVEMENTS_URL, {'search': 'Morning rush'})
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data['results']) == 1
        assert res.data['results'][0]['reason'] == 'SALE'

    def test_manual_receipt_has_null_purchase_order(self, client_a, movement_data):
        res = client_a.get(MOVEMENTS_URL, {'stock_batch': str(movement_data['manual_stock'].id)})
        receipt = next(row for row in res.data['results'] if row['reason'] == 'RECEIPT')
        assert receipt['purchase_order'] is None
        assert receipt['sales_order'] is None

    def test_po_receipt_has_purchase_order(self, client_a, movement_data):
        res = client_a.get(MOVEMENTS_URL, {'reason': 'RECEIPT', 'search': 'PO-LOT'})
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data['results']) == 1
        assert res.data['results'][0]['purchase_order']['title'] == 'PO-001 — Weekly dairy'
        assert res.data['results'][0]['sales_order'] is None

    def test_invalid_reason(self, client_a, movement_data):
        res = client_a.get(MOVEMENTS_URL, {'reason': 'INVALID'})
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_response_shape(self, client_a, movement_data):
        res = client_a.get(MOVEMENTS_URL, {'reason': 'SALE'})
        row = res.data['results'][0]
        assert set(row.keys()) == {
            'id', 'created_at', 'reason', 'delta', 'product',
            'stock_batch', 'sales_order', 'purchase_order',
        }
        assert set(row['product'].keys()) == {'id', 'name', 'sku', 'unit_of_measure'}
        assert set(row['stock_batch'].keys()) == {'id', 'lot_code'}
        assert set(row['sales_order'].keys()) == {'id', 'title', 'status'}


@pytest.mark.django_db
class TestStockBatchMovementsAPI:
    def test_batch_nested_route_matches_global_filter(self, client_a, movement_data):
        batch = movement_data['manual_stock']
        global_res = client_a.get(MOVEMENTS_URL, {'stock_batch': str(batch.id)})
        nested_res = client_a.get(f'{STOCKS_URL}{batch.id}/movements/')

        assert nested_res.status_code == status.HTTP_200_OK
        assert _movement_ids(global_res) == _movement_ids(nested_res)

    def test_batch_nested_route_other_user_404(self, client_a, client_b, movement_data):
        batch = movement_data['manual_stock']
        res = client_b.get(f'{STOCKS_URL}{batch.id}/movements/')
        assert res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestStockMovementReturnRows:
    def test_cancelled_sale_shows_sale_and_return(self, client_a, user_a, product_a):
        stock = Stock.objects.create(
            user=user_a,
            product=product_a,
            initial_quantity=Decimal('20'),
            current_quantity=Decimal('0'),
            unit_cost=Decimal('2.00'),
        )
        record_movement(
            user=user_a,
            stock_batch=stock,
            delta=Decimal('20'),
            reason=MovementReason.RECEIPT,
        )

        so = create_sales_order(
            user_a,
            [{'product_id': product_a.id, 'quantity': 5, 'unit_price': 4.00}],
            title='SO-cancelled',
        )
        confirm_sales_order(so)
        cancel_sales_order(so)

        res = client_a.get(MOVEMENTS_URL, {'search': 'SO-cancelled'})
        assert res.status_code == status.HTTP_200_OK
        reasons = {row['reason'] for row in res.data['results']}
        assert reasons == {'SALE', 'RETURN'}
        for row in res.data['results']:
            assert row['sales_order']['status'] == 'CANCELLED'
