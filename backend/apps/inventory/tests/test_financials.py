import pytest
from datetime import date, datetime
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import User
from apps.inventory.commands import record_movement
from apps.inventory.models import MovementReason, Product, Stock, StockMovement
from apps.inventory.selectors import get_overall_financials, get_products_with_financials
from apps.orders.commands import cancel_sales_order, confirm_sales_order, create_sales_order


def _aware(year, month, day):
    return timezone.make_aware(datetime(year, month, day, 12, 0, 0))


def _set_movement_dates(movements, when):
    movements.update(created_at=when)


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        username='test_user', email='test@example.com', password='Password123!'
    )


@pytest.fixture
def auth_client(test_user):
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=test_user)
    return client


@pytest.fixture
def financial_data(test_user):
    p1 = Product.objects.create(user=test_user, name="Product 1", sku="P1", unit_of_measure="KG")
    p2 = Product.objects.create(user=test_user, name="Product 2", sku="P2", unit_of_measure="L")

    stock1 = Stock.objects.create(
        user=test_user,
        product=p1,
        initial_quantity=Decimal('100'),
        current_quantity=Decimal('0'),
        unit_cost=Decimal('10.00'),
        lot_code="L1",
    )
    record_movement(
        user=test_user,
        stock_batch=stock1,
        delta=Decimal('100'),
        reason=MovementReason.RECEIPT,
    )

    stock2 = Stock.objects.create(
        user=test_user,
        product=p2,
        initial_quantity=Decimal('50'),
        current_quantity=Decimal('0'),
        unit_cost=Decimal('5.00'),
        lot_code="L2",
    )
    record_movement(
        user=test_user,
        stock_batch=stock2,
        delta=Decimal('50'),
        reason=MovementReason.RECEIPT,
    )

    so1 = create_sales_order(
        test_user,
        [{'product_id': p1.id, 'quantity': 20, 'unit_price': 25.00}],
    )
    confirm_sales_order(so1)

    so2 = create_sales_order(
        test_user,
        [{'product_id': p2.id, 'quantity': 10, 'unit_price': 10.00}],
    )
    confirm_sales_order(so2)

    return p1, p2, so1, so2


@pytest.mark.django_db
def test_overall_financials_empty_state(test_user):
    data = get_overall_financials(test_user)
    assert data['revenue'] == Decimal('0.00')
    assert data['cogs'] == Decimal('0.00')
    assert data['gross_profit'] == Decimal('0.00')
    assert data['margin'] == Decimal('0.00')
    assert data['inventory_value'] == Decimal('0.00')


@pytest.mark.django_db
def test_overall_financials_with_data(test_user, financial_data):
    data = get_overall_financials(test_user)
    assert data['revenue'] == Decimal('600.00')
    assert data['cogs'] == Decimal('250.00')
    assert data['gross_profit'] == Decimal('350.00')
    assert data['margin'] == Decimal('58.33')
    assert data['inventory_value'] == Decimal('1000.00')


@pytest.mark.django_db
def test_product_financials_with_data(test_user, financial_data):
    p1, p2, _, _ = financial_data
    products = get_products_with_financials(test_user)

    prod1 = products.get(id=p1.id)
    assert prod1.revenue == Decimal('500.00')
    assert prod1.cogs == Decimal('200.00')
    assert prod1.profit == Decimal('300.00')
    assert round(prod1.margin, 2) == Decimal('60.00')
    assert prod1.qty_purchased == Decimal('100.000')
    assert prod1.qty_sold == Decimal('20.000')

    prod2 = products.get(id=p2.id)
    assert prod2.revenue == Decimal('100.00')
    assert prod2.cogs == Decimal('50.00')
    assert prod2.profit == Decimal('50.00')
    assert round(prod2.margin, 2) == Decimal('50.00')
    assert prod2.qty_purchased == Decimal('50.000')
    assert prod2.qty_sold == Decimal('10.000')


@pytest.mark.django_db
def test_cogs_excludes_cancelled_sales_orders(test_user, financial_data):
    _, _, so1, so2 = financial_data

    data = get_overall_financials(test_user)
    assert data['cogs'] == Decimal('250.00')

    cancel_sales_order(so1)
    cancel_sales_order(so2)

    assert StockMovement.objects.filter(reason=MovementReason.SALE).count() == 2

    data = get_overall_financials(test_user)
    assert data['cogs'] == Decimal('0.00')
    assert data['revenue'] == Decimal('0.00')
    assert data['gross_profit'] == Decimal('0.00')

    products = get_products_with_financials(test_user)
    for product in products:
        assert product.qty_sold == Decimal('0.000')


@pytest.mark.django_db
def test_financials_api_endpoints(auth_client, financial_data):
    res = auth_client.get(reverse('inventory:overall-financials'))
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data['revenue'] == 600.00
    assert data['cogs'] == 250.00
    assert data['gross_profit'] == 350.00
    assert data['margin'] == 58.33
    assert data['inventory_value'] == 1000.00

    res = auth_client.get(reverse('inventory:product-financials'))
    assert res.status_code == status.HTTP_200_OK
    products = res.json()
    assert len(products) == 2

    p1_data = next(p for p in products if p['sku'] == 'P1')
    assert float(p1_data['revenue']) == 500.00
    assert float(p1_data['profit']) == 300.00
    assert float(p1_data['qty_purchased']) == 100.0
    assert float(p1_data['qty_sold']) == 20.0
    assert p1_data['unit_of_measure'] == 'KG'


@pytest.mark.django_db
def test_overall_financials_march_only(test_user, financial_data):
    p1, p2, _, _ = financial_data
    feb = _aware(2026, 2, 10)
    mar = _aware(2026, 3, 15)

    _set_movement_dates(
        StockMovement.objects.filter(stock_batch__product=p1, reason=MovementReason.RECEIPT),
        feb,
    )
    _set_movement_dates(
        StockMovement.objects.filter(stock_batch__product=p1, reason=MovementReason.SALE),
        mar,
    )
    _set_movement_dates(
        StockMovement.objects.filter(stock_batch__product=p2, reason=MovementReason.RECEIPT),
        mar,
    )
    _set_movement_dates(
        StockMovement.objects.filter(stock_batch__product=p2, reason=MovementReason.SALE),
        feb,
    )

    march = dict(date_from=date(2026, 3, 1), date_to=date(2026, 3, 31))
    data = get_overall_financials(test_user, **march)
    assert data['revenue'] == Decimal('500.00')
    assert data['cogs'] == Decimal('200.00')
    assert data['gross_profit'] == Decimal('300.00')
    assert data['inventory_value'] == Decimal('1000.00')

    products = get_products_with_financials(test_user, **march)
    prod1 = products.get(id=p1.id)
    prod2 = products.get(id=p2.id)
    assert prod1.revenue == Decimal('500.00')
    assert prod1.qty_sold == Decimal('20.000')
    assert prod1.qty_purchased == Decimal('0.000')
    assert prod2.revenue == Decimal('0.00')
    assert prod2.qty_sold == Decimal('0.000')
    assert prod2.qty_purchased == Decimal('50.000')


@pytest.mark.django_db
def test_period_revenue_aligns_with_multi_batch_sale(test_user):
    product = Product.objects.create(
        user=test_user, name='Multi', sku='MULTI', unit_of_measure='UNIT'
    )
    batch_a = Stock.objects.create(
        user=test_user,
        product=product,
        initial_quantity=Decimal('10'),
        current_quantity=Decimal('0'),
        unit_cost=Decimal('5.00'),
    )
    record_movement(
        user=test_user,
        stock_batch=batch_a,
        delta=Decimal('10'),
        reason=MovementReason.RECEIPT,
    )
    batch_b = Stock.objects.create(
        user=test_user,
        product=product,
        initial_quantity=Decimal('20'),
        current_quantity=Decimal('0'),
        unit_cost=Decimal('6.00'),
    )
    record_movement(
        user=test_user,
        stock_batch=batch_b,
        delta=Decimal('20'),
        reason=MovementReason.RECEIPT,
    )

    mar = _aware(2026, 3, 10)
    _set_movement_dates(StockMovement.objects.filter(reason=MovementReason.RECEIPT), mar)

    so = create_sales_order(
        test_user,
        [{'product_id': product.id, 'quantity': 15, 'unit_price': 15.00}],
    )
    confirm_sales_order(so)
    _set_movement_dates(
        StockMovement.objects.filter(reason=MovementReason.SALE, sales_order_item__order=so),
        mar,
    )

    march = dict(date_from=date(2026, 3, 1), date_to=date(2026, 3, 31))
    data = get_overall_financials(test_user, **march)
    assert data['revenue'] == Decimal('225.00')
    assert data['cogs'] == Decimal('80.00')
    assert data['gross_profit'] == Decimal('145.00')


@pytest.mark.django_db
def test_cancelled_sales_excluded_from_period(test_user, financial_data):
    _, _, so1, so2 = financial_data
    mar = _aware(2026, 3, 10)
    _set_movement_dates(StockMovement.objects.filter(reason=MovementReason.SALE), mar)

    march = dict(date_from=date(2026, 3, 1), date_to=date(2026, 3, 31))
    assert get_overall_financials(test_user, **march)['revenue'] == Decimal('600.00')

    cancel_sales_order(so1)
    cancel_sales_order(so2)

    data = get_overall_financials(test_user, **march)
    assert data['revenue'] == Decimal('0.00')
    assert data['cogs'] == Decimal('0.00')

    products = get_products_with_financials(test_user, **march)
    for product in products:
        assert product.qty_sold == Decimal('0.000')


@pytest.mark.django_db
def test_empty_period_returns_zeros(test_user, financial_data):
    april = dict(date_from=date(2026, 4, 1), date_to=date(2026, 4, 30))
    data = get_overall_financials(test_user, **april)
    assert data['revenue'] == Decimal('0.00')
    assert data['cogs'] == Decimal('0.00')
    assert data['gross_profit'] == Decimal('0.00')
    assert data['inventory_value'] == Decimal('1000.00')

    products = get_products_with_financials(test_user, **april)
    for product in products:
        assert product.revenue == Decimal('0.00')
        assert product.qty_sold == Decimal('0.000')


@pytest.mark.django_db
def test_financials_api_period_validation(auth_client, financial_data):
    base = reverse('inventory:overall-financials')

    res = auth_client.get(base, {'from': '2026-03-01'})
    assert res.status_code == status.HTTP_400_BAD_REQUEST

    res = auth_client.get(base, {'from': '2026-03-31', 'to': '2026-03-01'})
    assert res.status_code == status.HTTP_400_BAD_REQUEST

    res = auth_client.get(base, {'from': 'not-a-date', 'to': '2026-03-31'})
    assert res.status_code == status.HTTP_400_BAD_REQUEST

    res = auth_client.get(base, {'from': '2026-04-01', 'to': '2026-04-30'})
    assert res.status_code == status.HTTP_200_OK
    assert res.json()['revenue'] == 0.0

    mar = _aware(2026, 3, 10)
    _set_movement_dates(StockMovement.objects.filter(reason=MovementReason.SALE), mar)

    res = auth_client.get(base, {'from': '2026-03-01', 'to': '2026-03-31'})
    assert res.status_code == status.HTTP_200_OK
    assert res.json()['revenue'] == 600.0

    res = auth_client.get(
        reverse('inventory:product-financials'),
        {'from': '2026-03-01', 'to': '2026-03-31'},
    )
    assert res.status_code == status.HTTP_200_OK
    p2_data = next(p for p in res.json() if p['sku'] == 'P2')
    assert float(p2_data['qty_sold']) == 10.0
