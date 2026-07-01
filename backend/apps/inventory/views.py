from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from rest_framework import viewsets, status
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics

from apps.inventory.commands import record_movement
from apps.inventory.models import MovementReason, Product, Stock, UnitType
from apps.inventory.serializers import ProductSerializer, StockSerializer, ProductFinancialSerializer
from apps.inventory.financial_period import parse_financial_period
from apps.inventory.selectors import get_overall_financials, get_products_with_financials

VALID_UNIT_VALUES = {choice.value for choice in UnitType}


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    ordering = ["-created_at"]
    filter_backends = [SearchFilter]
    search_fields = ['name', 'sku', 'description']

    def get_queryset(self):
        """
        Strictly isolate data: users can only see their own products.
        Annotate the total stock calculated by PostgreSQL to avoid N+1 queries.
        Coalesce ensures that if there are no stock batches, the sum is 0 instead of None.

        Query params:
        - search: icontains match on name, sku, description (SearchFilter)
        - unit_of_measure: exact match (KG, G, L, ML, UNIT)
        - in_stock: true | false — filter by total_stock > 0 or == 0
        """
        queryset = Product.objects.filter(user=self.request.user).annotate(
            total_stock=Coalesce(
                Sum('stock_batches__current_quantity'),
                0,
                output_field=DecimalField()
            )
        )

        unit = self.request.query_params.get('unit_of_measure')
        if unit and unit in VALID_UNIT_VALUES:
            queryset = queryset.filter(unit_of_measure=unit)

        in_stock = self.request.query_params.get('in_stock')
        if in_stock is not None:
            normalized = in_stock.lower()
            if normalized in ('true', '1'):
                queryset = queryset.filter(total_stock__gt=0)
            elif normalized in ('false', '0'):
                queryset = queryset.filter(total_stock=0)

        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        """
        Forcefully inject the logged-in user as the owner of the product.
        """
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """
        Block deletion if any stock batches are still linked to this product.
        This preserves the financial cost-basis records for FIFO calculations.
        """
        product = self.get_object()
        if product.stock_batches.exists():
            return Response(
                {"detail": "Cannot delete a product with active stock batches. Remove all stock first."},
                status=status.HTTP_409_CONFLICT
            )
        return super().destroy(request, *args, **kwargs)

class StockViewSet(viewsets.ModelViewSet):
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]
    ordering = ["-created_at"]

    def get_queryset(self):
        """
        Strictly isolate data: users can only see their own stock batches.
        Optionally filter by product ID.
        """
        queryset = Stock.objects.filter(user=self.request.user).order_by('created_at')
        product_id = self.request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        initial = serializer.validated_data['initial_quantity']
        stock = serializer.save(
            user=self.request.user,
            initial_quantity=initial,
            current_quantity=Decimal('0'),
        )
        record_movement(
            user=self.request.user,
            stock_batch=stock,
            delta=initial,
            reason=MovementReason.RECEIPT,
        )

    @transaction.atomic
    def perform_update(self, serializer):
        stock = serializer.instance
        validated = serializer.validated_data

        new_current = validated.get('current_quantity', stock.current_quantity)
        new_initial = validated.get('initial_quantity', stock.initial_quantity)
        target_qty = new_current if 'current_quantity' in validated else new_initial

        delta = target_qty - stock.current_quantity
        if delta != 0:
            record_movement(
                user=self.request.user,
                stock_batch=stock,
                delta=delta,
                reason=MovementReason.ADJUSTMENT,
            )
            stock.initial_quantity += delta

        serializer.save()

    def destroy(self, request, *args, **kwargs):
        stock = self.get_object()
        if stock.movements.filter(reason=MovementReason.SALE).exists():
            return Response(
                {"detail": "Cannot delete a batch that has been used in a sale."},
                status=status.HTTP_409_CONFLICT,
            )
        if stock.current_quantity < stock.initial_quantity:
            return Response(
                {"detail": "Cannot delete a partially or fully consumed batch."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

class OverallFinancialsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_from, date_to = parse_financial_period(
            request.query_params.get('from'),
            request.query_params.get('to'),
        )
        financials = get_overall_financials(
            request.user,
            date_from=date_from,
            date_to=date_to,
        )
        return Response(financials)

class ProductFinancialsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProductFinancialSerializer
    pagination_class = None

    def get_queryset(self):
        date_from, date_to = parse_financial_period(
            self.request.query_params.get('from'),
            self.request.query_params.get('to'),
        )
        return get_products_with_financials(
            self.request.user,
            date_from=date_from,
            date_to=date_to,
        )
