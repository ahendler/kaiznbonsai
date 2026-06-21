from decimal import Decimal
from django.db.models import Sum, F, DecimalField, OuterRef, Subquery, Value, Case, When
from django.db.models.functions import Coalesce
from apps.orders.models import SalesOrderItem, OrderStatus
from apps.inventory.models import Stock, Product

def get_overall_financials(user) -> dict:
    revenue_agg = SalesOrderItem.objects.filter(
        order__user=user, 
        order__status=OrderStatus.CONFIRMED
    ).aggregate(
        total_revenue=Coalesce(
            Sum(F('quantity') * F('unit_price'), output_field=DecimalField()),
            Value(Decimal('0.00'), output_field=DecimalField())
        )
    )
    total_revenue = revenue_agg['total_revenue']

    cogs_agg = Stock.objects.filter(
        product__user=user
    ).aggregate(
        total_cogs=Coalesce(
            Sum((F('initial_quantity') - F('current_quantity')) * F('unit_cost'), output_field=DecimalField()),
            Value(Decimal('0.00'), output_field=DecimalField())
        ),
        inventory_value=Coalesce(
            Sum(F('current_quantity') * F('unit_cost'), output_field=DecimalField()),
            Value(Decimal('0.00'), output_field=DecimalField())
        )
    )
    total_cogs = cogs_agg['total_cogs']
    inventory_value = cogs_agg['inventory_value']

    gross_profit = total_revenue - total_cogs
    margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0.00')

    return {
        "revenue": round(total_revenue, 2),
        "cogs": round(total_cogs, 2),
        "gross_profit": round(gross_profit, 2),
        "margin": round(margin, 2),
        "inventory_value": round(inventory_value, 2)
    }

def get_products_with_financials(user):
    revenue_sq = SalesOrderItem.objects.filter(
        product=OuterRef('pk'),
        order__status=OrderStatus.CONFIRMED
    ).values('product').annotate(
        total=Sum(F('quantity') * F('unit_price'), output_field=DecimalField())
    ).values('total')

    cogs_sq = Stock.objects.filter(
        product=OuterRef('pk')
    ).values('product').annotate(
        total=Sum((F('initial_quantity') - F('current_quantity')) * F('unit_cost'), output_field=DecimalField())
    ).values('total')

    products = Product.objects.filter(user=user).annotate(
        revenue=Coalesce(Subquery(revenue_sq), Value(Decimal('0.00'), output_field=DecimalField())),
        cogs=Coalesce(Subquery(cogs_sq), Value(Decimal('0.00'), output_field=DecimalField())),
    ).annotate(
        profit=F('revenue') - F('cogs')
    ).annotate(
        margin=Case(
            When(revenue__gt=0, then=(F('profit') / F('revenue')) * 100.0),
            default=Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )
    )

    return products
