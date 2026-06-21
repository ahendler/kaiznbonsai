from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics

from apps.inventory.models import Product, Stock
from apps.inventory.serializers import ProductSerializer, StockSerializer, ProductFinancialSerializer
from apps.inventory.selectors import get_overall_financials, get_products_with_financials

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    ordering = ["-created_at"]

    def get_queryset(self):
        """
        Strictly isolate data: users can only see their own products.
        Annotate the total stock calculated by PostgreSQL to avoid N+1 queries.
        Coalesce ensures that if there are no stock batches, the sum is 0 instead of None.
        """
        return Product.objects.filter(user=self.request.user).annotate(
            total_stock=Coalesce(
                Sum('stock_batches__current_quantity'), 
                0, 
                output_field=DecimalField()
            )
        ).order_by('-created_at')

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

    def perform_create(self, serializer):
        """
        Forcefully inject the logged-in user as the owner of the stock batch.
        Note: The serializer already validated that the chosen Product belongs to this user.
        """
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """
        Block deletion if the batch has been partially or fully consumed.
        """
        stock = self.get_object()
        if stock.current_quantity < stock.initial_quantity:
            return Response(
                {"detail": "Cannot delete a partially or fully consumed batch."},
                status=status.HTTP_409_CONFLICT
            )
        return super().destroy(request, *args, **kwargs)

class OverallFinancialsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        financials = get_overall_financials(request.user)
        return Response(financials)

class ProductFinancialsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProductFinancialSerializer
    pagination_class = None

    def get_queryset(self):
        return get_products_with_financials(self.request.user)
