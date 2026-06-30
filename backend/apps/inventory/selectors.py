from decimal import Decimal

from django.db.models import Sum, F, DecimalField, OuterRef, Subquery, Value, Case, When
from django.db.models.functions import Coalesce

from apps.inventory.models import MovementReason, Product, Stock, StockMovement
from apps.orders.models import OrderStatus, SalesOrderItem


def get_overall_financials(user) -> dict:
    revenue_agg = SalesOrderItem.objects.filter(
        order__user=user,
        order__status=OrderStatus.CONFIRMED,
    ).aggregate(
        total_revenue=Coalesce(
            Sum(F('quantity') * F('unit_price'), output_field=DecimalField()),
            Value(Decimal('0.00'), output_field=DecimalField()),
        )
    )
    total_revenue = revenue_agg['total_revenue']

    cogs_agg = StockMovement.objects.filter(
        user=user,
        reason=MovementReason.SALE,
        sales_order_item__order__status=OrderStatus.CONFIRMED,
    ).aggregate(
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


def get_products_with_financials(user):
    revenue_sq = SalesOrderItem.objects.filter(
        product=OuterRef('pk'),
        order__status=OrderStatus.CONFIRMED,
    ).values('product').annotate(
        total=Sum(F('quantity') * F('unit_price'), output_field=DecimalField())
    ).values('total')

    cogs_sq = StockMovement.objects.filter(
        stock_batch__product=OuterRef('pk'),
        user=user,
        reason=MovementReason.SALE,
        sales_order_item__order__status=OrderStatus.CONFIRMED,
    ).values('stock_batch__product').annotate(
        total=Sum(-F('delta') * F('stock_batch__unit_cost'), output_field=DecimalField())
    ).values('total')

    qty_sold_sq = StockMovement.objects.filter(
        stock_batch__product=OuterRef('pk'),
        user=user,
        reason=MovementReason.SALE,
        sales_order_item__order__status=OrderStatus.CONFIRMED,
    ).values('stock_batch__product').annotate(
        total=Sum(-F('delta'), output_field=DecimalField())
    ).values('total')

    qty_purchased_sq = StockMovement.objects.filter(
        stock_batch__product=OuterRef('pk'),
        user=user,
        reason=MovementReason.RECEIPT,
    ).values('stock_batch__product').annotate(
        total=Sum(F('delta'), output_field=DecimalField())
    ).values('total')

    zero_qty = Value(Decimal('0.000'), output_field=DecimalField(max_digits=12, decimal_places=3))

    products = Product.objects.filter(user=user).annotate(
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

    return products
