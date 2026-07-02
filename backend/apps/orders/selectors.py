from django.db.models import QuerySet
from apps.orders.models import PurchaseOrder, SalesOrder

def get_purchase_orders_for_user(user, *, status: str | None = None) -> QuerySet[PurchaseOrder]:
    queryset = (
        PurchaseOrder.objects.filter(user=user)
        .prefetch_related('items__product')
        .order_by('-created_at')
    )
    if status is not None:
        queryset = queryset.filter(status=status)
    return queryset


def get_sales_orders_for_user(user, *, status: str | None = None) -> QuerySet[SalesOrder]:
    queryset = (
        SalesOrder.objects.filter(user=user)
        .prefetch_related('items__product')
        .order_by('-created_at')
    )
    if status is not None:
        queryset = queryset.filter(status=status)
    return queryset
