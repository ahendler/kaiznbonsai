from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics

from apps.core.pagination import ProductFinancialsCursorPagination, StockMovementCursorPagination
from apps.inventory.commands import (
    BATCH_ALREADY_VOIDED,
    BATCH_NO_REMAINING_QTY,
    record_movement,
    void_manual_stock_batch,
)
from apps.inventory.models import MovementReason, Product, Stock, UnitType
from apps.inventory.serializers import (
    ProductSerializer,
    StockSerializer,
    ProductFinancialSerializer,
    StockMovementListSerializer,
)
from apps.inventory.financial_period import parse_financial_period
from apps.inventory.financial_product_filters import (
    parse_activity,
    parse_margin_band,
    parse_ordering,
    parse_search,
)
from apps.inventory.movement_filters import (
    parse_movement_reasons,
    parse_product_id,
    parse_stock_batch_id,
)
from apps.inventory.selectors import (
    get_overall_financials,
    get_products_with_financials,
    list_stock_movements,
)

VALID_UNIT_VALUES = {choice.value for choice in UnitType}


def build_movement_queryset(request, *, stock_batch_id=None):
    date_from, date_to = parse_financial_period(
        request.query_params.get('from'),
        request.query_params.get('to'),
    )
    return list_stock_movements(
        request.user,
        reasons=parse_movement_reasons(request.query_params.get('reason')),
        product_id=parse_product_id(request.query_params.get('product')),
        stock_batch_id=stock_batch_id if stock_batch_id is not None else parse_stock_batch_id(
            request.query_params.get('stock_batch'),
        ),
        date_from=date_from,
        date_to=date_to,
        search=parse_search(request.query_params.get('search')),
    )


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

    def get_queryset(self, include_voided: bool | None = None):
        """
        Strictly isolate data: users can only see their own stock batches.
        Optionally filter by product ID. Voided batches are hidden unless
        ?include_voided=true is passed (or include_voided=True for internal lookups).
        """
        queryset = Stock.objects.filter(user=self.request.user).order_by('created_at')
        product_id = self.request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        if include_voided is None:
            include_voided = self.request.query_params.get('include_voided', '').lower() in ('true', '1')
        if not include_voided:
            queryset = queryset.filter(voided_at__isnull=True)
        return queryset

    def _get_stock_batch(self, *, include_voided: bool = False) -> Stock:
        return get_object_or_404(self.get_queryset(include_voided=include_voided), pk=self.kwargs['pk'])

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

        stock = serializer.save()
        self._sync_po_item_batch_metadata(stock, validated)

    def _sync_po_item_batch_metadata(self, stock: Stock, validated: dict) -> None:
        """Keep PO line lot/best-before in sync when batch metadata is edited."""
        if not stock.purchase_order_item_id:
            return
        po_item = stock.purchase_order_item
        update_fields = []
        if 'lot_code' in validated and po_item.lot_code != stock.lot_code:
            po_item.lot_code = stock.lot_code
            update_fields.append('lot_code')
        if 'best_before' in validated and po_item.best_before != stock.best_before:
            po_item.best_before = stock.best_before
            update_fields.append('best_before')
        if update_fields:
            po_item.save(update_fields=update_fields)

    def destroy(self, request, *args, **kwargs):
        # Enforce auth and tenant scoping before returning 405 (ledger batches are never deleted).
        self.get_object()
        return Response(
            {
                'detail': (
                    'Stock batches cannot be deleted. '
                    'Use POST /inventory/stocks/{id}/void/ to void a manual batch.'
                ),
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        stock = self._get_stock_batch(include_voided=True)
        try:
            stock = void_manual_stock_batch(user=request.user, stock_batch=stock)
        except DjangoValidationError as exc:
            messages = exc.messages if hasattr(exc, 'messages') else [str(exc)]
            detail = messages[0] if len(messages) == 1 else messages
            status_code = status.HTTP_409_CONFLICT
            if detail in {BATCH_NO_REMAINING_QTY, BATCH_ALREADY_VOIDED}:
                status_code = status.HTTP_400_BAD_REQUEST
            return Response({'detail': detail}, status=status_code)

        serializer = self.get_serializer(stock)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def movements(self, request, pk=None):
        stock = self.get_object()
        queryset = build_movement_queryset(request, stock_batch_id=stock.id)
        paginator = StockMovementCursorPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = StockMovementListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

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
    pagination_class = ProductFinancialsCursorPagination

    def get_queryset(self):
        date_from, date_to = parse_financial_period(
            self.request.query_params.get('from'),
            self.request.query_params.get('to'),
        )
        return get_products_with_financials(
            self.request.user,
            date_from=date_from,
            date_to=date_to,
            search=parse_search(self.request.query_params.get('search')),
            margin_band=parse_margin_band(self.request.query_params.get('margin_band')),
            activity=parse_activity(self.request.query_params.get('activity')),
            ordering=parse_ordering(self.request.query_params.get('ordering')),
        )


class StockMovementListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StockMovementListSerializer
    pagination_class = StockMovementCursorPagination

    def get_queryset(self):
        return build_movement_queryset(self.request)
