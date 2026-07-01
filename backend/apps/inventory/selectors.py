from datetime import date
from decimal import Decimal

from django.db.models import Sum, F, DecimalField, OuterRef, Subquery, Value, Case, When, Q
from django.db.models.functions import Coalesce

from apps.inventory.models import MovementReason, Product, Stock, StockMovement
from apps.orders.models import OrderStatus


def _movement_date_filter(qs, *, date_from: date | None, date_to: date | None):
    if date_from is None:
        return qs
    return qs.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    )


def _confirmed_sale_movements(user, *, date_from: date | None = None, date_to: date | None = None):
    qs = StockMovement.objects.filter(
        user=user,
        reason=MovementReason.SALE,
        sales_order_item__order__status=OrderStatus.CONFIRMED,
        sales_order_item__isnull=False,
    )
    return _movement_date_filter(qs, date_from=date_from, date_to=date_to)


def _receipt_movements(user, *, date_from: date | None = None, date_to: date | None = None):
    qs = StockMovement.objects.filter(
        user=user,
        reason=MovementReason.RECEIPT,
    )
    return _movement_date_filter(qs, date_from=date_from, date_to=date_to)


def get_overall_financials(
    user,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    sale_movements = _confirmed_sale_movements(user, date_from=date_from, date_to=date_to)

    revenue_agg = sale_movements.aggregate(
        total_revenue=Coalesce(
            Sum(
                -F('delta') * F('sales_order_item__unit_price'),
                output_field=DecimalField(),
            ),
            Value(Decimal('0.00'), output_field=DecimalField()),
        )
    )
    total_revenue = revenue_agg['total_revenue']

    cogs_agg = sale_movements.aggregate(
        total_cogs=Coalesce(
            Sum(-F('delta') * F('stock_batch__unit_cost'), output_field=DecimalField()),
            Value(Decimal('0.00'), output_field=DecimalField()),
        )
    )
    total_cogs = cogs_agg['total_cogs']

    inventory_agg = Stock.objects.filter(product__user=user).aggregate(
        inventory_value=Coalesce(
            Sum(F('current_quantity') * F('unit_cost'), output_field=DecimalField()),
            Value(Decimal('0.00'), output_field=DecimalField()),
        )
    )
    inventory_value = inventory_agg['inventory_value']

    gross_profit = total_revenue - total_cogs
    margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0.00')

    return {
        "revenue": round(total_revenue, 2),
        "cogs": round(total_cogs, 2),
        "gross_profit": round(gross_profit, 2),
        "margin": round(margin, 2),
        "inventory_value": round(inventory_value, 2),
    }


def _apply_margin_band_filter(qs, margin_band: str | None):
    if margin_band is None:
        return qs
    if margin_band == 'negative':
        return qs.filter(profit__lt=0)
    if margin_band == 'low':
        return qs.filter(profit__gte=0, margin__lt=20)
    if margin_band == 'medium':
        return qs.filter(margin__gte=20, margin__lt=40)
    if margin_band == 'high':
        return qs.filter(margin__gte=40)
    return qs


def get_products_with_financials(
    user,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    margin_band: str | None = None,
    activity: str = 'all',
):
    products = Product.objects.filter(user=user)
    if search:
        products = products.filter(Q(name__icontains=search) | Q(sku__icontains=search))

    sale_movements = _confirmed_sale_movements(user, date_from=date_from, date_to=date_to)
    receipt_movements = _receipt_movements(user, date_from=date_from, date_to=date_to)

    revenue_sq = sale_movements.filter(
        stock_batch__product=OuterRef('pk'),
    ).values('stock_batch__product').annotate(
        total=Sum(
            -F('delta') * F('sales_order_item__unit_price'),
            output_field=DecimalField(),
        )
    ).values('total')

    cogs_sq = sale_movements.filter(
        stock_batch__product=OuterRef('pk'),
    ).values('stock_batch__product').annotate(
        total=Sum(-F('delta') * F('stock_batch__unit_cost'), output_field=DecimalField())
    ).values('total')

    qty_sold_sq = sale_movements.filter(
        stock_batch__product=OuterRef('pk'),
    ).values('stock_batch__product').annotate(
        total=Sum(-F('delta'), output_field=DecimalField())
    ).values('total')

    qty_purchased_sq = receipt_movements.filter(
        stock_batch__product=OuterRef('pk'),
    ).values('stock_batch__product').annotate(
        total=Sum(F('delta'), output_field=DecimalField())
    ).values('total')

    zero_qty = Value(Decimal('0.000'), output_field=DecimalField(max_digits=12, decimal_places=3))

    products = products.annotate(
        revenue=Coalesce(Subquery(revenue_sq), Value(Decimal('0.00'), output_field=DecimalField())),
        cogs=Coalesce(Subquery(cogs_sq), Value(Decimal('0.00'), output_field=DecimalField())),
        qty_sold=Coalesce(Subquery(qty_sold_sq), zero_qty),
        qty_purchased=Coalesce(Subquery(qty_purchased_sq), zero_qty),
    ).annotate(
        profit=F('revenue') - F('cogs')
    ).annotate(
        margin=Case(
            When(revenue__gt=0, then=(F('profit') / F('revenue')) * 100.0),
            default=Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )

    products = _apply_margin_band_filter(products, margin_band)

    if activity == 'movement':
        products = products.filter(Q(qty_purchased__gt=0) | Q(qty_sold__gt=0))
    elif activity == 'stale':
        products = products.filter(qty_purchased=0, qty_sold=0)

    return products.order_by('-created_at')
