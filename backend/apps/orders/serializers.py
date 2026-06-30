from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.inventory.serializers import ProductSerializer
from apps.orders.constants import StockAllocationStrategy
from apps.orders.validators import validate_products_belong_to_user

from .models import PurchaseOrder, PurchaseOrderItem, SalesOrder, SalesOrderItem


def _validate_owned_product_id(value, context):
    request = context.get('request')
    if request and request.user:
        try:
            validate_products_belong_to_user(request.user, {value})
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)[0]) from exc
    return value


class PurchaseOrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.DecimalField(
        max_digits=12, decimal_places=3, min_value=Decimal('0.001')
    )
    unit_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0')
    )
    lot_code = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default=''
    )
    best_before = serializers.DateField(required=False, allow_null=True, default=None)

    def validate_product_id(self, value):
        return _validate_owned_product_id(value, self.context)


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'product_id', 'product_details', 'quantity',
            'unit_cost', 'lot_code', 'best_before',
        ]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    items_data = PurchaseOrderItemInputSerializer(many=True, write_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'title', 'status', 'order_date', 'created_at',
            'updated_at', 'items', 'items_data',
        ]
        read_only_fields = ['status', 'order_date', 'created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is None:
            self.fields['items_data'].required = True

    def validate_items_data(self, value):
        if not value:
            raise serializers.ValidationError(
                "A purchase order must have at least one item."
            )
        return value


class SalesOrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.DecimalField(
        max_digits=12, decimal_places=3, min_value=Decimal('0.001')
    )
    unit_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0')
    )

    def validate_product_id(self, value):
        return _validate_owned_product_id(value, self.context)


class SalesOrderItemSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = SalesOrderItem
        fields = ['id', 'product_id', 'product_details', 'quantity', 'unit_price']


class SalesOrderSerializer(serializers.ModelSerializer):
    items = SalesOrderItemSerializer(many=True, read_only=True)
    items_data = SalesOrderItemInputSerializer(many=True, write_only=True)

    class Meta:
        model = SalesOrder
        fields = [
            'id', 'title', 'status', 'order_date', 'created_at',
            'updated_at', 'items', 'items_data',
        ]
        read_only_fields = ['status', 'order_date', 'created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is None:
            self.fields['items_data'].required = True

    def validate_items_data(self, value):
        if not value:
            raise serializers.ValidationError(
                "A sales order must have at least one item."
            )
        return value


class ConfirmSalesOrderSerializer(serializers.Serializer):
    allocation_strategy = serializers.ChoiceField(
        choices=StockAllocationStrategy.choices,
        default=StockAllocationStrategy.FIFO,
        required=False,
    )
