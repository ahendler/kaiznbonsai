from django.contrib import admin
from apps.orders.models import PurchaseOrder, PurchaseOrderItem, SalesOrder, SalesOrderItem

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'order_date']
    list_filter = ['status', 'order_date']
    inlines = [PurchaseOrderItemInline]

class SalesOrderItemInline(admin.TabularInline):
    model = SalesOrderItem
    extra = 1

@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'order_date']
    list_filter = ['status', 'order_date']
    inlines = [SalesOrderItemInline]
