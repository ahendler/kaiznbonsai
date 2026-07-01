import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.core.management import call_command
from django.db.models import Sum
from django.utils import timezone

from apps.inventory.models import MovementReason, Product, Stock, StockMovement, UnitType
from apps.inventory.selectors import get_overall_financials, get_products_with_financials
from apps.orders.models import OrderStatus, PurchaseOrder, SalesOrder


def _last_month_range(today: date) -> tuple[date, date]:
    first_this_month = today.replace(day=1)
    last_month_end = first_this_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    return last_month_start, last_month_end


@pytest.mark.django_db
@pytest.mark.integration
def test_generate_seed_data_command():
    """Smoke test: runs against the ephemeral CI database only (demo@example.com tenant)."""
    call_command('generate_seed_data')

    products = Product.objects.filter(user__email='demo@example.com')
    assert products.count() == 19

    units = set(products.values_list('unit_of_measure', flat=True))
    assert units == {UnitType.KG, UnitType.G, UnitType.L, UnitType.ML, UnitType.UNIT}

    pos = PurchaseOrder.objects.filter(user__email='demo@example.com')
    sos = SalesOrder.objects.filter(user__email='demo@example.com')
    assert pos.count() == 18
    assert sos.count() == 19
    assert pos.filter(status=OrderStatus.DRAFT).exists()
    assert pos.filter(status=OrderStatus.CANCELLED).exists()
    assert sos.filter(status=OrderStatus.DRAFT).exists()
    assert sos.filter(status=OrderStatus.CANCELLED).exists()

    demo_user = products.first().user
    overall = get_overall_financials(demo_user)
    assert overall['revenue'] > Decimal('0')
    assert overall['cogs'] > Decimal('0')

    product_financials = list(get_products_with_financials(demo_user))
    assert len(product_financials) == 19

    with_sales = [p for p in product_financials if p.revenue > 0]
    without_sales = [p for p in product_financials if p.revenue == 0]
    assert len(with_sales) >= 12
    assert len(without_sales) >= 2

    negative_margin = [p for p in with_sales if p.profit < 0]
    assert len(negative_margin) >= 1

    cinnamon = products.get(sku='SPIC-CIN-01')
    cinnamon_stock = cinnamon.stock_batches.aggregate(total=Sum('current_quantity'))['total']
    assert cinnamon_stock == Decimal('0')

    unsold_skus = {'SUP-PRO-01', 'BEV-SPK-01'}
    unsold = {p.sku for p in without_sales}
    assert unsold_skus.issubset(unsold)

    multi_batch_products = sum(1 for p in products if p.stock_batches.count() >= 2)
    assert multi_batch_products >= 17

    movement_months = {
        (m.created_at.year, m.created_at.month)
        for m in StockMovement.objects.filter(user=demo_user)
    }
    assert len(movement_months) >= 3

    today = timezone.now().date()
    this_month_start = today.replace(day=1)
    last_month_start, last_month_end = _last_month_range(today)

    this_month = get_overall_financials(
        demo_user,
        date_from=this_month_start,
        date_to=today,
    )
    last_month = get_overall_financials(
        demo_user,
        date_from=last_month_start,
        date_to=last_month_end,
    )
    assert this_month['revenue'] > Decimal('0')
    assert last_month['revenue'] > Decimal('0')

    assert StockMovement.objects.filter(
        user=demo_user,
        reason=MovementReason.VOID,
    ).exists()
    assert StockMovement.objects.filter(
        user=demo_user,
        reason=MovementReason.RECEIPT_REVERSAL,
    ).exists()
    assert Stock.objects.filter(user=demo_user, voided_at__isnull=False).exists()
