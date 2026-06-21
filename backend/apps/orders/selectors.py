from django.db.models import QuerySet
from apps.orders.models import PurchaseOrder, SalesOrder

def get_purchase_orders_for_user(user) -> QuerySet[PurchaseOrder]:
    return PurchaseOrder.objects.filter(user=user).prefetch_related('items__product').order_by('-created_at')

def get_sales_orders_for_user(user) -> QuerySet[SalesOrder]:
    return SalesOrder.objects.filter(user=user).prefetch_related('items__product').order_by('-created_at')
