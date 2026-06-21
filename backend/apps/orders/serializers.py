from rest_framework import serializers
from apps.inventory.serializers import ProductSerializer
from .models import PurchaseOrder, PurchaseOrderItem, SalesOrder, SalesOrderItem

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = ['id', 'product_id', 'product_details', 'quantity', 'unit_cost', 'lot_code', 'best_before']

class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    items_data = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )

    class Meta:
        model = PurchaseOrder
        fields = ['id', 'title', 'status', 'order_date', 'created_at', 'updated_at', 'items', 'items_data']
        read_only_fields = ['status', 'order_date', 'created_at', 'updated_at']


class SalesOrderItemSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = SalesOrderItem
        fields = ['id', 'product_id', 'product_details', 'quantity', 'unit_price']

class SalesOrderSerializer(serializers.ModelSerializer):
    items = SalesOrderItemSerializer(many=True, read_only=True)
    items_data = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )

    class Meta:
        model = SalesOrder
        fields = ['id', 'title', 'status', 'order_date', 'created_at', 'updated_at', 'items', 'items_data']
        read_only_fields = ['status', 'order_date', 'created_at', 'updated_at']
