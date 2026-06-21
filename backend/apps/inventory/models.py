import uuid
from django.db import models
from simple_history.models import HistoricalRecords
from apps.core.models import TenantOwnedModel

class UnitType(models.TextChoices):
    KG = "KG", "Kilogram"
    G = "G", "Gram"
    L = "L", "Liter"
    ML = "ML", "Milliliter"
    UNIT = "UNIT", "Unit"

class Product(TenantOwnedModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    sku = models.CharField(max_length=100)
    unit_of_measure = models.CharField(max_length=10, choices=UnitType.choices, default=UnitType.UNIT)
    history = HistoricalRecords()

    class Meta:
        db_table = "inventory_products"
        unique_together = [("user", "sku")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.sku})"

class Stock(TenantOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_batches")
    lot_code = models.CharField(max_length=100, blank=True, default="")
    best_before = models.DateField(null=True, blank=True)
    purchase_order_item = models.ForeignKey('orders.PurchaseOrderItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_batches')
    initial_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    current_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    history = HistoricalRecords()

    class Meta:
        db_table = "inventory_stocks"
        ordering = ["created_at"]  # Oldest first for FIFO

    def __str__(self):
        return f"{self.product.name} - Batch {self.lot_code or self.id.hex[:8]} ({self.current_quantity})"
