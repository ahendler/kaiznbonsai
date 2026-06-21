from django.db import models
from django.conf import settings
from apps.inventory.models import Product
from apps.core.models import TenantOwnedModel

class OrderStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    CANCELLED = 'CANCELLED', 'Cancelled'

class PurchaseOrder(TenantOwnedModel):
    title = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.DRAFT)
    order_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"PO #{self.id} - {self.get_status_display()}"

class PurchaseOrderItem(models.Model):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='purchase_order_items')
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    lot_code = models.CharField(max_length=50, blank=True, null=True)
    best_before = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (PO #{self.order.id})"

class SalesOrder(TenantOwnedModel):
    title = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.DRAFT)
    order_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"SO #{self.id} - {self.get_status_display()}"

class SalesOrderItem(models.Model):
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sales_order_items')
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (SO #{self.order.id})"
