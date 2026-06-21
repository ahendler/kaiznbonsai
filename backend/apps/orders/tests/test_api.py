import pytest
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.inventory.models import Product, Stock
from apps.orders.models import PurchaseOrder, SalesOrder, OrderStatus

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user():
    return User.objects.create_user(username="test@example.com", email="test@example.com", password="password")

@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client

@pytest.fixture
def product(user):
    return Product.objects.create(
        user=user,
        name="Matcha",
        sku="MATCHA-1",
        unit_of_measure="UNIT"
    )

@pytest.mark.django_db
class TestPurchaseOrderAPI:
    def test_create_purchase_order(self, authenticated_client, product):
        url = '/api/v1/orders/purchase-orders/'
        data = {
            'items_data': [
                {'product_id': product.id, 'quantity': 100, 'unit_cost': 10.50, 'lot_code': 'LOT1'}
            ]
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == 201
        assert response.data['status'] == OrderStatus.DRAFT
        assert len(response.data['items']) == 1
        assert PurchaseOrder.objects.count() == 1

    def test_confirm_purchase_order(self, authenticated_client, product, user):
        po = PurchaseOrder.objects.create(user=user, status=OrderStatus.DRAFT)
        po.items.create(product=product, quantity=100, unit_cost=10.50, lot_code='LOT1')
        
        url = f'/api/v1/orders/purchase-orders/{po.id}/confirm/'
        response = authenticated_client.post(url)
        assert response.status_code == 200
        assert response.data['status'] == OrderStatus.CONFIRMED
        assert Stock.objects.count() == 1

@pytest.mark.django_db
class TestSalesOrderAPI:
    def test_create_sales_order(self, authenticated_client, product):
        url = '/api/v1/orders/sales-orders/'
        data = {
            'items_data': [
                {'product_id': product.id, 'quantity': 50, 'unit_price': 20.00}
            ]
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == 201
        assert response.data['status'] == OrderStatus.DRAFT
        assert len(response.data['items']) == 1
        assert SalesOrder.objects.count() == 1

    def test_confirm_sales_order_success(self, authenticated_client, product, user):
        Stock.objects.create(user=user, product=product, initial_quantity=100, current_quantity=100, unit_cost=10.00)
        
        so = SalesOrder.objects.create(user=user, status=OrderStatus.DRAFT)
        so.items.create(product=product, quantity=50, unit_price=20.00)
        
        url = f'/api/v1/orders/sales-orders/{so.id}/confirm/'
        response = authenticated_client.post(url)
        assert response.status_code == 200
        assert response.data['status'] == OrderStatus.CONFIRMED
        assert Stock.objects.first().current_quantity == 50

    def test_confirm_sales_order_insufficient_stock(self, authenticated_client, product, user):
        so = SalesOrder.objects.create(user=user, status=OrderStatus.DRAFT)
        so.items.create(product=product, quantity=50, unit_price=20.00)
        
        url = f'/api/v1/orders/sales-orders/{so.id}/confirm/'
        response = authenticated_client.post(url)
        assert response.status_code == 400
        assert "Insufficient stock" in response.data[0]
