from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError

from .models import PurchaseOrder, SalesOrder
from .serializers import PurchaseOrderSerializer, SalesOrderSerializer
from .commands import (
    create_purchase_order, confirm_purchase_order, cancel_purchase_order,
    create_sales_order, confirm_sales_order, cancel_sales_order
)

class PurchaseOrderViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseOrderSerializer

    def get_queryset(self):
        return PurchaseOrder.objects.filter(user=self.request.user).prefetch_related('items__product')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items_data = serializer.validated_data.get('items_data', [])
        
        try:
            order = create_purchase_order(request.user, items_data)
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

class SalesOrderViewSet(viewsets.ModelViewSet):
    serializer_class = SalesOrderSerializer

    def get_queryset(self):
        return SalesOrder.objects.filter(user=self.request.user).prefetch_related('items__product')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items_data = serializer.validated_data.get('items_data', [])
        
        try:
            order = create_sales_order(request.user, items_data)
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict if hasattr(e, 'message_dict') else list(e.messages))
            
        return Response(self.get_serializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        order = self.get_object()
        try:
            order = confirm_sales_order(order)
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
