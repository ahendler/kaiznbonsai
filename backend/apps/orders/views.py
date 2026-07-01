from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError

from apps.inventory.models import StockMovement
from .serializers import PurchaseOrderSerializer, SalesOrderSerializer, ConfirmSalesOrderSerializer
from .selectors import get_purchase_orders_for_user, get_sales_orders_for_user
from .commands import (
    create_purchase_order, confirm_purchase_order, cancel_purchase_order,
    create_sales_order, confirm_sales_order, cancel_sales_order
)

class PurchaseOrderViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return get_purchase_orders_for_user(self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items_data = serializer.validated_data.get('items_data', [])
        title = serializer.validated_data.get('title')
        
        try:
            order = create_purchase_order(request.user, items_data, title=title)
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict if hasattr(e, 'message_dict') else list(e.messages))
            
        return Response(self.get_serializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        order = self.get_object()
        try:
            order = confirm_purchase_order(order)
        except DjangoValidationError as e:
            raise ValidationError(list(e.messages))
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        try:
            order = cancel_purchase_order(order)
        except DjangoValidationError as e:
            raise ValidationError(list(e.messages))
        return Response(self.get_serializer(order).data)

    def destroy(self, request, *args, **kwargs):
        order = self.get_object()
        if StockMovement.objects.filter(purchase_order_item__order=order).exists():
            return Response(
                {
                    'detail': (
                        'Cannot delete a purchase order that has stock movement history.'
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

class SalesOrderViewSet(viewsets.ModelViewSet):
    serializer_class = SalesOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return get_sales_orders_for_user(self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items_data = serializer.validated_data.get('items_data', [])
        title = serializer.validated_data.get('title')
        
        try:
            order = create_sales_order(request.user, items_data, title=title)
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict if hasattr(e, 'message_dict') else list(e.messages))
            
        return Response(self.get_serializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        order = self.get_object()
        serializer = ConfirmSalesOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = confirm_sales_order(
                order,
                allocation_strategy=serializer.validated_data['allocation_strategy'],
            )
        except DjangoValidationError as e:
            raise ValidationError(list(e.messages))
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        try:
            order = cancel_sales_order(order)
        except DjangoValidationError as e:
            raise ValidationError(list(e.messages))
        return Response(self.get_serializer(order).data)

    def destroy(self, request, *args, **kwargs):
        order = self.get_object()
        if StockMovement.objects.filter(sales_order_item__order=order).exists():
            return Response(
                {
                    'detail': (
                        'Cannot delete a sales order that has stock movement history.'
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)
