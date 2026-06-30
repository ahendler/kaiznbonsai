import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.inventory.commands import record_movement
from apps.inventory.models import MovementReason, Product, Stock
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


def make_stock_with_receipt(user, product, quantity, unit_cost=Decimal('10.00')):
    stock = Stock.objects.create(
        user=user,
        product=product,
        initial_quantity=Decimal(str(quantity)),
        current_quantity=Decimal('0'),
        unit_cost=unit_cost,
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

    def test_delete_draft_purchase_order_returns_204(self, authenticated_client, product, user):
        po = PurchaseOrder.objects.create(user=user, status=OrderStatus.DRAFT)
        po.items.create(product=product, quantity=100, unit_cost=10.50, lot_code='LOT1')

        response = authenticated_client.delete(f'/api/v1/orders/purchase-orders/{po.id}/')
        assert response.status_code == 204
        assert not PurchaseOrder.objects.filter(id=po.id).exists()

    def test_delete_confirmed_purchase_order_returns_409(self, authenticated_client, product, user):
        po = PurchaseOrder.objects.create(user=user, status=OrderStatus.DRAFT)
        po.items.create(product=product, quantity=100, unit_cost=10.50, lot_code='LOT1')
        authenticated_client.post(f'/api/v1/orders/purchase-orders/{po.id}/confirm/')

        response = authenticated_client.delete(f'/api/v1/orders/purchase-orders/{po.id}/')
        assert response.status_code == 409
        assert PurchaseOrder.objects.filter(id=po.id).exists()

    def test_create_purchase_order_rejects_empty_items(self, authenticated_client):
        response = authenticated_client.post(
            '/api/v1/orders/purchase-orders/',
            {'items_data': []},
            format='json',
        )
        assert response.status_code == 400
        assert PurchaseOrder.objects.count() == 0

    def test_create_purchase_order_rejects_missing_unit_cost(self, authenticated_client, product):
        response = authenticated_client.post(
            '/api/v1/orders/purchase-orders/',
            {
                'items_data': [
                    {'product_id': product.id, 'quantity': 100, 'lot_code': 'LOT1'}
                ]
            },
            format='json',
        )
        assert response.status_code == 400
        assert PurchaseOrder.objects.count() == 0

    def test_create_purchase_order_rejects_invalid_quantity(self, authenticated_client, product):
        response = authenticated_client.post(
            '/api/v1/orders/purchase-orders/',
            {
                'items_data': [
                    {'product_id': product.id, 'quantity': 0, 'unit_cost': 10.50}
                ]
            },
            format='json',
        )
        assert response.status_code == 400
        assert PurchaseOrder.objects.count() == 0

    def test_cannot_create_purchase_order_with_another_users_product(self, api_client):
        owner = User.objects.create_user(
            username="po-owner@example.com", email="po-owner@example.com", password="password"
        )
        attacker = User.objects.create_user(
            username="po-attacker@example.com", email="po-attacker@example.com", password="password"
        )
        product = Product.objects.create(
            user=owner, name="Owner Product", sku="PO-OWN-1", unit_of_measure="UNIT"
        )
        api_client.force_authenticate(user=attacker)

        response = api_client.post(
            '/api/v1/orders/purchase-orders/',
            {
                'items_data': [
                    {'product_id': product.id, 'quantity': 10, 'unit_cost': 5.00}
                ]
            },
            format='json',
        )
        assert response.status_code == 400
        assert PurchaseOrder.objects.count() == 0

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
        stock = make_stock_with_receipt(user, product, 100)

        so = SalesOrder.objects.create(user=user, status=OrderStatus.DRAFT)
        so.items.create(product=product, quantity=50, unit_price=20.00)

        url = f'/api/v1/orders/sales-orders/{so.id}/confirm/'
        response = authenticated_client.post(url)
        assert response.status_code == 200
        assert response.data['status'] == OrderStatus.CONFIRMED

        stock.refresh_from_db()
        assert stock.current_quantity == Decimal('50.000')
        assert stock.movements.filter(reason=MovementReason.SALE).count() == 1

    def test_confirm_sales_order_insufficient_stock(self, authenticated_client, product, user):
        so = SalesOrder.objects.create(user=user, status=OrderStatus.DRAFT)
        so.items.create(product=product, quantity=50, unit_price=20.00)
        
        url = f'/api/v1/orders/sales-orders/{so.id}/confirm/'
        response = authenticated_client.post(url)
        assert response.status_code == 400
        assert "Insufficient stock" in response.data[0]

    def test_create_sales_order_rejects_empty_items(self, authenticated_client):
        response = authenticated_client.post(
            '/api/v1/orders/sales-orders/',
            {'items_data': []},
            format='json',
        )
        assert response.status_code == 400
        assert SalesOrder.objects.count() == 0

    def test_create_sales_order_rejects_missing_unit_price(self, authenticated_client, product):
        response = authenticated_client.post(
            '/api/v1/orders/sales-orders/',
            {
                'items_data': [
                    {'product_id': product.id, 'quantity': 50}
                ]
            },
            format='json',
        )
        assert response.status_code == 400
        assert SalesOrder.objects.count() == 0

    def test_create_sales_order_rejects_invalid_quantity(self, authenticated_client, product):
        response = authenticated_client.post(
            '/api/v1/orders/sales-orders/',
            {
                'items_data': [
                    {'product_id': product.id, 'quantity': -5, 'unit_price': 20.00}
                ]
            },
            format='json',
        )
        assert response.status_code == 400
        assert SalesOrder.objects.count() == 0

    def test_cannot_create_sales_order_with_another_users_product(self, api_client):
        owner = User.objects.create_user(
            username="owner@example.com", email="owner@example.com", password="password"
        )
        attacker = User.objects.create_user(
            username="attacker@example.com", email="attacker@example.com", password="password"
        )
        product = Product.objects.create(
            user=owner, name="Owner Product", sku="OWN-1", unit_of_measure="UNIT"
        )
        api_client.force_authenticate(user=attacker)

        url = '/api/v1/orders/sales-orders/'
        data = {
            'items_data': [
                {'product_id': product.id, 'quantity': 10, 'unit_price': 20.00}
            ]
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == 400
        assert SalesOrder.objects.count() == 0

    def test_confirm_sales_order_cannot_drain_another_users_stock(self, api_client):
        owner = User.objects.create_user(
            username="owner2@example.com", email="owner2@example.com", password="password"
        )
        attacker = User.objects.create_user(
            username="attacker2@example.com", email="attacker2@example.com", password="password"
        )
        product = Product.objects.create(
            user=owner, name="Protected Stock", sku="PRT-1", unit_of_measure="UNIT"
        )
        stock = make_stock_with_receipt(owner, product, 100)

        so = SalesOrder.objects.create(user=attacker, status=OrderStatus.DRAFT)
        so.items.create(product=product, quantity=50, unit_price=20.00)
        api_client.force_authenticate(user=attacker)

        url = f'/api/v1/orders/sales-orders/{so.id}/confirm/'
        response = api_client.post(url)
        assert response.status_code == 400

        stock.refresh_from_db()
        assert stock.current_quantity == Decimal('100.000')
        assert stock.movements.filter(reason=MovementReason.SALE).count() == 0

    def test_delete_draft_sales_order_returns_204(self, authenticated_client, user, product):
        so = SalesOrder.objects.create(user=user, status=OrderStatus.DRAFT)
        so.items.create(product=product, quantity=50, unit_price=20.00)

        response = authenticated_client.delete(f'/api/v1/orders/sales-orders/{so.id}/')
        assert response.status_code == 204
        assert not SalesOrder.objects.filter(id=so.id).exists()

    def test_delete_confirmed_sales_order_returns_409(self, authenticated_client, user, product):
        make_stock_with_receipt(user, product, 100)
        so = SalesOrder.objects.create(user=user, status=OrderStatus.DRAFT)
        so.items.create(product=product, quantity=50, unit_price=20.00)
        authenticated_client.post(f'/api/v1/orders/sales-orders/{so.id}/confirm/')

        response = authenticated_client.delete(f'/api/v1/orders/sales-orders/{so.id}/')
        assert response.status_code == 409
        assert SalesOrder.objects.filter(id=so.id).exists()

    def test_delete_cancelled_sales_order_returns_204(self, authenticated_client, user, product):
        make_stock_with_receipt(user, product, 100)
        so = SalesOrder.objects.create(user=user, status=OrderStatus.DRAFT)
        so.items.create(product=product, quantity=50, unit_price=20.00)
        authenticated_client.post(f'/api/v1/orders/sales-orders/{so.id}/confirm/')
        authenticated_client.post(f'/api/v1/orders/sales-orders/{so.id}/cancel/')

        response = authenticated_client.delete(f'/api/v1/orders/sales-orders/{so.id}/')
        assert response.status_code == 204
        assert not SalesOrder.objects.filter(id=so.id).exists()
