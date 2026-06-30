from django.db.models import F, QuerySet

from apps.inventory.models import Stock
from apps.orders.constants import StockAllocationStrategy


def available_batches_for_allocation(
    *,
    user,
    product,
    strategy: str,
) -> QuerySet[Stock]:
    qs = Stock.objects.filter(
        user=user,
        product=product,
        current_quantity__gt=0,
    )
    if strategy == StockAllocationStrategy.FEFO:
        return qs.order_by(F('best_before').asc(nulls_last=True), 'created_at')
    return qs.order_by('created_at')
