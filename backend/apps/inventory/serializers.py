from rest_framework import serializers
from apps.inventory.models import Product, Stock

class ProductSerializer(serializers.ModelSerializer):
    # This field will be populated by a database annotation in the ViewSet
    total_stock = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True, default=0)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'sku', 'unit_of_measure', 
            'total_stock', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'total_stock', 'created_at', 'updated_at']

    def validate_sku(self, value):
        """
        Ensure SKU is unique *per user*, allowing different users to use the same SKU.
        """
        request = self.context.get('request')
        if request and request.user:
            qs = Product.objects.filter(user=request.user, sku=value)
            # If updating an existing product, exclude it from the duplicate check
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("A product with this SKU already exists in your inventory.")
        return value

class StockSerializer(serializers.ModelSerializer):
    # Helpful read-only fields for the frontend so it doesn't have to make extra API calls
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)

    class Meta:
        model = Stock
        fields = [
            'id', 'product', 'product_name', 'product_sku', 'lot_code', 
            'best_before', 'initial_quantity', 'current_quantity', 
            'unit_cost', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'product_name', 'product_sku', 
            'created_at', 'updated_at'
        ]

    def validate_initial_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Initial quantity cannot be negative.")
        return value

    def validate_current_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Current quantity cannot be negative.")
        return value

    def validate_product(self, value):
        """
        Crucial security check: Ensure the user owns the product they are adding stock to.
        """
        request = self.context.get('request')
        if request and request.user:
            if value.user_id != request.user.id:
                raise serializers.ValidationError("You can only add stock to your own products.")
        return value

    def validate(self, data):
        """
        Enforce business rules for stock editing.
        """
        if self.instance: # Update operation
            is_consumed = self.instance.current_quantity < self.instance.initial_quantity
            
            # 1. Block initial_quantity edits if consumed
            new_initial_qty = data.get('initial_quantity', self.instance.initial_quantity)
            if is_consumed and new_initial_qty != self.instance.initial_quantity:
                raise serializers.ValidationError({
                    "initial_quantity": "Cannot edit initial quantity because this batch has been partially or fully consumed."
                })
            
            # 2. current_quantity is read-only
            if 'current_quantity' in data and data['current_quantity'] != self.instance.current_quantity:
                raise serializers.ValidationError({
                    "current_quantity": "Current quantity is read-only and cannot be manually updated here."
                })

        return data
