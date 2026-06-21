import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from apps.inventory.models import Product, Stock
from apps.orders.models import PurchaseOrder, PurchaseOrderItem, SalesOrder, SalesOrderItem, OrderStatus
from apps.inventory.selectors import get_overall_financials, get_products_with_financials

from apps.accounts.models import User

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
    # Create products
    p1 = Product.objects.create(user=test_user, name="Product 1", sku="P1", unit_of_measure="KG")
    p2 = Product.objects.create(user=test_user, name="Product 2", sku="P2", unit_of_measure="L")

    # Product 1: 100 units at $10 each. Total Cost = $1000
    Stock.objects.create(
        user=test_user, product=p1, initial_quantity=Decimal('100'), 
        current_quantity=Decimal('100'), unit_cost=Decimal('10.00'), lot_code="L1"
    )

    # Product 2: 50 units at $5 each. Total Cost = $250
    Stock.objects.create(
        user=test_user, product=p2, initial_quantity=Decimal('50'), 
        current_quantity=Decimal('50'), unit_cost=Decimal('5.00'), lot_code="L2"
    )

    # Sell 20 units of Product 1 at $25 each (Revenue = 500, COGS = 200, Profit = 300)
    # Deduct stock manually since we're setting up the DB state directly
    stock1 = Stock.objects.get(lot_code="L1")
    stock1.current_quantity = Decimal('80')
    stock1.save()

    so1 = SalesOrder.objects.create(user=test_user, status=OrderStatus.CONFIRMED)
    SalesOrderItem.objects.create(order=so1, product=p1, quantity=Decimal('20'), unit_price=Decimal('25.00'))

    # Sell 10 units of Product 2 at $10 each (Revenue = 100, COGS = 50, Profit = 50)
    stock2 = Stock.objects.get(lot_code="L2")
    stock2.current_quantity = Decimal('40')
    stock2.save()

    so2 = SalesOrder.objects.create(user=test_user, status=OrderStatus.CONFIRMED)
    SalesOrderItem.objects.create(order=so2, product=p2, quantity=Decimal('10'), unit_price=Decimal('10.00'))

    # Total Expected Overall:
    # Revenue: 500 + 100 = 600
    # COGS: 200 + 50 = 250
    # Profit: 600 - 250 = 350
    # Margin: (350 / 600) * 100 = 58.33
    # Inventory Value: (80 * 10) + (40 * 5) = 800 + 200 = 1000

    return p1, p2

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
    p1, p2 = financial_data
    products = get_products_with_financials(test_user)
    
    # Assert Product 1
    prod1 = products.get(id=p1.id)
    assert prod1.revenue == Decimal('500.00')
    assert prod1.cogs == Decimal('200.00')
    assert prod1.profit == Decimal('300.00')
    assert round(prod1.margin, 2) == Decimal('60.00')

    # Assert Product 2
    prod2 = products.get(id=p2.id)
    assert prod2.revenue == Decimal('100.00')
    assert prod2.cogs == Decimal('50.00')
    assert prod2.profit == Decimal('50.00')
    assert round(prod2.margin, 2) == Decimal('50.00')

@pytest.mark.django_db
def test_financials_api_endpoints(auth_client, financial_data):
    # Test overall API
    res = auth_client.get(reverse('inventory:overall-financials'))
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data['revenue'] == 600.00
    assert data['cogs'] == 250.00
    assert data['gross_profit'] == 350.00
    assert data['margin'] == 58.33
    assert data['inventory_value'] == 1000.00

    # Test products API
    res = auth_client.get(reverse('inventory:product-financials'))
    assert res.status_code == status.HTTP_200_OK
    products = res.json()
    assert len(products) == 2
    
    p1_data = next(p for p in products if p['sku'] == 'P1')
    assert float(p1_data['revenue']) == 500.00
    assert float(p1_data['profit']) == 300.00
