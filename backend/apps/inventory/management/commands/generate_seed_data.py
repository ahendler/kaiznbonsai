import os
import sys
import random
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.inventory.models import Product, Stock
from apps.orders.models import PurchaseOrder, PurchaseOrderItem, SalesOrder, SalesOrderItem, OrderStatus
from apps.orders.commands import confirm_purchase_order, confirm_sales_order, cancel_purchase_order, cancel_sales_order

User = get_user_model()

class Command(BaseCommand):
    help = 'Generates synthetic food and beverage seed data for testing and demonstrations'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting data generation...")
        try:
            with transaction.atomic():
                self.generate()
            self.stdout.write(self.style.SUCCESS('Successfully generated seed data!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error generating data: {str(e)}"))
            raise

    def generate(self):
        # 1. Create User
        email = "demo@example.com"
        user = User.objects.filter(email=email).first()
        if not user:
            user = User.objects.create_user(
                username=email,
                email=email,
                password="Password123!"
            )
            self.stdout.write(f"Created user {email}")
        else:
            # Wipe existing data for this user to ensure clean state
            self.stdout.write("Wiping existing data for user...")
            SalesOrder.objects.filter(user=user).delete()
            PurchaseOrder.objects.filter(user=user).delete()
            Stock.objects.filter(user=user).delete()
            Product.objects.filter(user=user).delete()

        # 2. Create Products
        p_coff = Product.objects.create(user=user, name="Espresso Beans", sku="COFF-01", unit_of_measure="KG", description="Dark roast")
        p_oat = Product.objects.create(user=user, name="Oat Milk", sku="OAT-01", unit_of_measure="L", description="Barista grade")
        p_mat = Product.objects.create(user=user, name="Matcha", sku="MAT-01", unit_of_measure="KG", description="Powder")
        p_kmb = Product.objects.create(user=user, name="Kombucha", sku="KMB-01", unit_of_measure="EA", description="Ginger flavor")
        p_bag = Product.objects.create(user=user, name="Filter Bags", sku="BAG-01", unit_of_measure="EA", description="Size 4")

        self.stdout.write("Created Products")

        # Helper for PO
        def create_po(title, items):
            po = PurchaseOrder.objects.create(user=user, title=title)
            for item in items:
                # Unpack variable length tuple (product, qty, cost, best_before=None)
                prod = item[0]
                qty = item[1]
                cost = item[2]
                best_before = item[3] if len(item) > 3 else None
                PurchaseOrderItem.objects.create(
                    order=po, 
                    product=prod, 
                    quantity=Decimal(qty), 
                    unit_cost=Decimal(cost),
                    best_before=best_before
                )
            return po

        # Helper for SO
        def create_so(title, items):
            so = SalesOrder.objects.create(user=user, title=title)
            for prod, qty, price in items:
                SalesOrderItem.objects.create(order=so, product=prod, quantity=Decimal(qty), unit_price=Decimal(price))
            return so

        now = timezone.now().date()

        # 3. Purchase Orders
        po1 = create_po("PO-001 (Initial Stockup)", [
            (p_coff, "1000", "12.00", now + timedelta(days=90)),
            (p_oat, "500", "1.50", now + timedelta(days=30))
        ])
        confirm_purchase_order(po1)

        po2 = create_po("PO-002 (Tea & Supplies)", [
            (p_mat, "100", "40.00", now + timedelta(days=180)),
            (p_bag, "5000", "0.10") # Filter bags don't expire
        ])
        confirm_purchase_order(po2)

        po3 = create_po("PO-003 (Kombucha Drop)", [
            (p_kmb, "2000", "1.20", now + timedelta(days=14)) # Short shelf life
        ])
        confirm_purchase_order(po3)

        po4 = create_po("PO-004 (Restock Espresso at higher cost)", [
            (p_coff, "500", "14.00", now + timedelta(days=120))
        ])
        confirm_purchase_order(po4)

        po5 = create_po("PO-005 (Supplier Backout)", [
            (p_oat, "1000", "1.60")
        ])
        cancel_purchase_order(po5) # Remains cancelled

        po6 = create_po("PO-006 (Alternative Oat Milk Restock)", [
            (p_oat, "500", "1.60", now + timedelta(days=45))
        ])
        confirm_purchase_order(po6)

        self.stdout.write("Processed Purchase Orders")

        # 4. Generate 40 small orders to showcase infinite scrolling with random price variance
        self.stdout.write("Generating 40 bulk orders for UI testing...")
        for i in range(1, 41):
            kmb_price = f"{3.50 + random.uniform(-0.20, 0.20):.2f}"
            bag_price = f"{0.50 + random.uniform(-0.20, 0.20):.2f}"
            bulk_so = create_so(f"SO-BULK-{i:03d} (Walk-in Customer)", [
                (p_kmb, "1", kmb_price),
                (p_bag, "2", bag_price)
            ])
            confirm_sales_order(bulk_so)

        # 5. Sales Orders
        so1 = create_so("SO-001 (Local Cafe)", [
            (p_coff, "100", "25.00"),
            (p_oat, "50", "4.00")
        ])
        confirm_sales_order(so1)

        so2 = create_so("SO-002 (Retail Chain)", [
            (p_kmb, "500", "3.50"),
            (p_mat, "20", "90.00")
        ])
        confirm_sales_order(so2)

        so3 = create_so("SO-003 (Wholesale Deal Fell Through)", [
            (p_coff, "200", "24.00")
        ])
        confirm_sales_order(so3)
        cancel_sales_order(so3) # Cancel it after confirming to trigger refund logic

        so4 = create_so("SO-004 (Large Distributor)", [
            (p_coff, "950", "22.00") # Consumes 900 from PO1 and 50 from PO4
        ])
        confirm_sales_order(so4)

        so5 = create_so("SO-005 (Cafe Restock)", [
            (p_bag, "1000", "0.30"),
            (p_oat, "100", "4.00")
        ])
        confirm_sales_order(so5)

        so6 = create_so("SO-006 (Pending Negotiation)", [
            (p_kmb, "100", "3.50")
        ])
        # Leave SO6 in DRAFT state

        self.stdout.write("Processed Sales Orders")
