from dataclasses import dataclass
from decimal import Decimal
from datetime import date, datetime, time, timedelta
import calendar
import os
from typing import Literal, Optional

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.inventory.commands import record_movement, void_manual_stock_batch
from apps.inventory.models import MovementReason, Product, Stock, StockMovement, UnitType
from apps.orders.models import PurchaseOrder, PurchaseOrderItem, SalesOrder, SalesOrderItem
from apps.orders.commands import (
    cancel_purchase_order,
    cancel_sales_order,
    confirm_purchase_order,
    confirm_sales_order,
)

User = get_user_model()

DEMO_EMAIL = 'demo@example.com'
DEMO_PASSWORD_ENV = 'DEMO_USER_PASSWORD'


@dataclass(frozen=True)
class ProductSpec:
    sku: str
    name: str
    unit: str
    description: str


@dataclass(frozen=True)
class PoLineSpec:
    sku: str
    quantity: str
    unit_cost: str
    best_before_days: Optional[int] = None
    lot_code: str = ''


@dataclass(frozen=True)
class SoLineSpec:
    sku: str
    quantity: str
    unit_price: str


PoAction = Literal['confirm', 'cancel', 'confirm_cancel', 'draft']
SoAction = Literal['confirm', 'cancel', 'draft']
ActivityWhen = tuple[int, int]  # (months_ago, day_of_month) — 0 = current month
PoSeedEntry = tuple[str, list[PoLineSpec], PoAction] | tuple[str, list[PoLineSpec], PoAction, ActivityWhen]
SoSeedEntry = tuple[str, list[SoLineSpec], SoAction] | tuple[str, list[SoLineSpec], SoAction, ActivityWhen]


# Specialty coffee & beverage supply catalog — covers every UnitType.
DEMO_PRODUCTS: tuple[ProductSpec, ...] = (
    ProductSpec('COFF-ESP-01', 'Espresso Beans — House Blend', UnitType.KG, 'Medium-dark roast with notes of chocolate and caramel.'),
    ProductSpec('COFF-DEC-01', 'Decaf Arabica — Swiss Water', UnitType.KG, 'Chemical-free decaffeination; smooth finish for evening service.'),
    ProductSpec('DAIR-OAT-01', 'Oat Milk — Barista Edition', UnitType.L, 'Steam-stable oat milk formulated for latte art.'),
    ProductSpec('DAIR-ALM-01', 'Almond Milk — Unsweetened', UnitType.L, 'Light almond profile; no added sugar.'),
    ProductSpec('DAIR-CRM-01', 'Heavy Cream', UnitType.ML, '36% butterfat; whipping and sauce applications.'),
    ProductSpec('SYRP-VAN-01', 'Vanilla Syrup', UnitType.ML, 'Classic café syrup for lattes, sodas, and baking.'),
    ProductSpec('TEA-MAT-01', 'Matcha — Ceremonial Grade', UnitType.G, 'Stone-ground Uji matcha for drinks and baking.'),
    ProductSpec('SPIC-CIN-01', 'Cinnamon — Ground Ceylon', UnitType.G, 'Sweet, delicate Ceylon cinnamon for pastries and chai.'),
    ProductSpec('SYRP-HON-01', 'Honey — Local Wildflower', UnitType.KG, 'Raw wildflower honey from regional apiaries.'),
    ProductSpec('BAKE-COC-01', 'Cocoa Powder — Dutch Process', UnitType.KG, 'Rich alkalized cocoa for brownies and hot chocolate.'),
    ProductSpec('BEV-CHAI-01', 'Chai Concentrate', UnitType.L, 'Black tea and spice concentrate; dilute 1:4 for service.'),
    ProductSpec('BEV-CBR-01', 'Cold Brew Concentrate', UnitType.L, '12-hour steep concentrate; dilute 1:3 over ice.'),
    ProductSpec('BEV-KMB-01', 'Kombucha — Ginger Lemongrass', UnitType.UNIT, '12 oz bottles; live culture, lightly carbonated.'),
    ProductSpec('BEV-SPK-01', 'Sparkling Water — Glass', UnitType.L, '750 mL glass bottles; neutral mineral profile.'),
    ProductSpec('SUP-FLT-04', 'Filter Bags — Size #4', UnitType.UNIT, 'Bleached paper filters for pour-over and batch brewers.'),
    ProductSpec('SUP-CUP-12', 'Paper Cups — 12 oz', UnitType.UNIT, 'Double-wall compostable cups for hot drinks.'),
    ProductSpec('SUP-LID-01', 'Biodegradable Lids — 12 oz', UnitType.UNIT, 'PLA-lined sip lids; fits 12 oz cups.'),
    ProductSpec('SUP-PRO-01', 'Protein Powder — Vanilla Whey', UnitType.KG, 'Whey isolate for smoothie programs; recently added to catalog.'),
    ProductSpec('BAKE-CNS-01', 'Coconut Sugar', UnitType.KG, 'Unrefined palm sugar; lower glycemic alternative to cane.'),
)


class Command(BaseCommand):
    help = 'Generates realistic food & beverage demo data for reviewers and local development'

    def handle(self, *args, **options):
        self._demo_password = self._require_demo_password()

        self.stdout.write('Starting demo seed generation...')
        try:
            with transaction.atomic():
                catalog = self.generate()
            self._print_credentials()
            self._print_summary(catalog)
            self.stdout.write(self.style.SUCCESS('Successfully generated demo seed data!'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Error generating data: {exc}'))
            raise

    def generate(self) -> dict[str, Product]:
        user = self._get_or_reset_demo_user()
        catalog = self._create_products(user)
        today = timezone.now().date()

        self._seed_purchase_orders(user, catalog, today)
        self._seed_sales_orders(user, catalog)
        self._seed_ledger_void_examples(user, catalog)

        return catalog

    def _require_demo_password(self) -> str:
        password = os.environ.get(DEMO_PASSWORD_ENV, '').strip()
        if not password:
            raise CommandError(
                f'{DEMO_PASSWORD_ENV} environment variable is required to seed the demo account.'
            )
        return password

    def _get_or_reset_demo_user(self):
        password = self._demo_password
        user = User.objects.filter(email=DEMO_EMAIL).first()
        if not user:
            user = User.objects.create_user(
                username=DEMO_EMAIL,
                email=DEMO_EMAIL,
                password=password,
            )
            self.stdout.write(f'Created demo user {DEMO_EMAIL}')
            return user

        self.stdout.write('Resetting existing demo tenant data...')
        SalesOrder.objects.filter(user=user).delete()
        PurchaseOrder.objects.filter(user=user).delete()
        Product.objects.filter(user=user).delete()
        user.set_password(password)
        user.save(update_fields=['password'])
        return user

    def _create_products(self, user) -> dict[str, Product]:
        catalog: dict[str, Product] = {}
        for spec in DEMO_PRODUCTS:
            catalog[spec.sku] = Product.objects.create(
                user=user,
                sku=spec.sku,
                name=spec.name,
                unit_of_measure=spec.unit,
                description=spec.description,
            )
        self.stdout.write(f'Created {len(catalog)} products')
        return catalog

    def _seed_purchase_orders(self, user, catalog: dict[str, Product], today):
        # Multiple PO lines for the same SKU create separate FIFO batches on confirm.
        purchase_orders: list[PoSeedEntry] = [
            (
                'PO-001 — Atlas Coffee Importers (opening stock)',
                [
                    PoLineSpec('COFF-ESP-01', '500', '12.00', 180, 'ESP-HB-2401A'),
                    PoLineSpec('COFF-ESP-01', '300', '12.00', 150, 'ESP-HB-2401B'),
                    PoLineSpec('COFF-DEC-01', '120', '11.00', 180, 'DEC-SW-2401A'),
                    PoLineSpec('COFF-DEC-01', '80', '11.00', 160, 'DEC-SW-2401B'),
                ],
                'confirm',
                (4, 8),
            ),
            (
                'PO-002 — Pacific Alt Dairy Co.',
                [
                    PoLineSpec('DAIR-OAT-01', '350', '1.50', 45, 'OAT-BAR-2402A'),
                    PoLineSpec('DAIR-OAT-01', '250', '1.48', 40, 'OAT-BAR-2402B'),
                    PoLineSpec('DAIR-ALM-01', '250', '1.35', 45, 'ALM-UNSW-2402A'),
                    PoLineSpec('DAIR-ALM-01', '150', '1.33', 42, 'ALM-UNSW-2402B'),
                    PoLineSpec('DAIR-CRM-01', '30000', '0.003', 30, 'CRM-36-2402A'),
                    PoLineSpec('DAIR-CRM-01', '20000', '0.003', 28, 'CRM-36-2402B'),
                ],
                'confirm',
                (4, 15),
            ),
            (
                'PO-003 — Monsoon Syrups & Concentrates',
                [
                    PoLineSpec('SYRP-VAN-01', '6000', '0.008', 365, 'VAN-SYR-2403A'),
                    PoLineSpec('SYRP-VAN-01', '4000', '0.008', 340, 'VAN-SYR-2403B'),
                    PoLineSpec('BEV-CHAI-01', '120', '4.50', 120, 'CHAI-CON-2403A'),
                    PoLineSpec('BEV-CHAI-01', '80', '4.45', 110, 'CHAI-CON-2403B'),
                    PoLineSpec('BEV-CBR-01', '90', '6.00', 90, 'CBR-CON-2403A'),
                    PoLineSpec('BEV-CBR-01', '60', '5.95', 85, 'CBR-CON-2403B'),
                ],
                'confirm',
                (3, 6),
            ),
            (
                'PO-004 — Kyoto Tea Exchange',
                [
                    PoLineSpec('TEA-MAT-01', '6000', '0.08', 365, 'MAT-CER-2404A'),
                    PoLineSpec('TEA-MAT-01', '4000', '0.081', 350, 'MAT-CER-2404B'),
                    PoLineSpec('SPIC-CIN-01', '3000', '0.012', 540, 'CIN-CEY-2404A'),
                    PoLineSpec('SPIC-CIN-01', '2000', '0.014', 480, 'CIN-CEY-2404B'),
                    PoLineSpec('BAKE-COC-01', '60', '8.00', 730, 'COC-DUT-2404A'),
                    PoLineSpec('BAKE-COC-01', '40', '8.10', 700, 'COC-DUT-2404B'),
                ],
                'confirm',
                (3, 14),
            ),
            (
                'PO-005 — GreenPack Disposables',
                [
                    PoLineSpec('SUP-FLT-04', '6000', '0.08', lot_code='FLT-04-2405A'),
                    PoLineSpec('SUP-FLT-04', '4000', '0.079', lot_code='FLT-04-2405B'),
                    PoLineSpec('SUP-CUP-12', '3000', '0.06', lot_code='CUP-12-2405A'),
                    PoLineSpec('SUP-CUP-12', '2000', '0.058', lot_code='CUP-12-2405B'),
                    PoLineSpec('SUP-LID-01', '3000', '0.04', lot_code='LID-12-2405A'),
                    PoLineSpec('SUP-LID-01', '2000', '0.039', lot_code='LID-12-2405B'),
                ],
                'confirm',
                (3, 22),
            ),
            (
                'PO-006 — Ferment & Fizz Wholesale',
                [
                    PoLineSpec('BEV-KMB-01', '450', '1.18', 28, 'KMB-GNG-2406A'),
                    PoLineSpec('BEV-KMB-01', '350', '1.22', 21, 'KMB-GNG-2406B'),
                    PoLineSpec('BEV-SPK-01', '350', '0.88', 365, 'SPK-GLS-2406A'),
                    PoLineSpec('BEV-SPK-01', '250', '0.90', 360, 'SPK-GLS-2406B'),
                ],
                'confirm',
                (3, 28),
            ),
            (
                'PO-007 — Bee & Bake Specialty',
                [
                    PoLineSpec('SYRP-HON-01', '90', '9.50', 540, 'HON-WLF-2407A'),
                    PoLineSpec('SYRP-HON-01', '60', '9.45', 520, 'HON-WLF-2407B'),
                    PoLineSpec('BAKE-CNS-01', '50', '4.20', 365, 'CNS-PALM-2407A'),
                    PoLineSpec('BAKE-CNS-01', '30', '4.15', 350, 'CNS-PALM-2407B'),
                ],
                'confirm',
                (2, 7),
            ),
            (
                'PO-008 — Atlas Coffee Importers (Q2 restock — higher cost)',
                [
                    PoLineSpec('COFF-ESP-01', '250', '14.50', 120, 'ESP-HB-2408A'),
                    PoLineSpec('COFF-ESP-01', '150', '14.75', 110, 'ESP-HB-2408B'),
                ],
                'confirm',
                (2, 15),
            ),
            (
                'PO-009 — Pacific Alt Dairy Co. (supplier backout after receipt)',
                [
                    PoLineSpec('DAIR-OAT-01', '100', '1.65', 60, 'OAT-BACKOUT-2409'),
                ],
                'confirm_cancel',
                (1, 3),
            ),
            (
                'PO-010 — Pacific Alt Dairy Co. (alternate oat shipment)',
                [
                    PoLineSpec('DAIR-OAT-01', '180', '1.55', 50, 'OAT-BAR-2410A'),
                    PoLineSpec('DAIR-OAT-01', '120', '1.52', 48, 'OAT-BAR-2410B'),
                ],
                'confirm',
                (2, 23),
            ),
            (
                'PO-011 — NutriBlend Direct (new SKU trial)',
                [
                    PoLineSpec('SUP-PRO-01', '35', '18.00', 365, 'PRO-VAN-2411A'),
                    PoLineSpec('SUP-PRO-01', '25', '17.80', 350, 'PRO-VAN-2411B'),
                ],
                'confirm',
                (1, 5),
            ),
            (
                'PO-012 — Summit Paper Goods (Q3 cups quote)',
                [
                    PoLineSpec('SUP-CUP-12', '8000', '0.055'),
                    PoLineSpec('SUP-LID-01', '8000', '0.038'),
                ],
                'draft',
            ),
            (
                'PO-013 — Pacific Alt Dairy Co. (April restock)',
                [
                    PoLineSpec('DAIR-ALM-01', '120', '1.38', 44, 'ALM-UNSW-2413A'),
                    PoLineSpec('DAIR-ALM-01', '80', '1.40', 42, 'ALM-UNSW-2413B'),
                    PoLineSpec('DAIR-CRM-01', '15000', '0.0032', 25, 'CRM-36-2413A'),
                    PoLineSpec('DAIR-CRM-01', '10000', '0.0031', 22, 'CRM-36-2413B'),
                ],
                'confirm',
                (1, 12),
            ),
            (
                'PO-014 — Monsoon Syrups (vanilla top-up)',
                [
                    PoLineSpec('SYRP-VAN-01', '3000', '0.0085', 330, 'VAN-SYR-2414A'),
                    PoLineSpec('SYRP-VAN-01', '2000', '0.0088', 310, 'VAN-SYR-2414B'),
                ],
                'confirm',
                (1, 19),
            ),
            (
                'PO-015 — Ferment & Fizz (kombucha replenishment)',
                [
                    PoLineSpec('BEV-KMB-01', '220', '1.20', 24, 'KMB-GNG-2415A'),
                    PoLineSpec('BEV-KMB-01', '180', '1.24', 18, 'KMB-GNG-2415B'),
                ],
                'confirm',
                (1, 26),
            ),
            (
                'PO-016 — Kyoto Tea Exchange (matcha restock)',
                [
                    PoLineSpec('TEA-MAT-01', '2500', '0.082', 340, 'MAT-CER-2416A'),
                    PoLineSpec('TEA-MAT-01', '1500', '0.084', 320, 'MAT-CER-2416B'),
                ],
                'confirm',
                (0, 6),
            ),
            (
                'PO-017 — Atlas Coffee Importers (decaf restock)',
                [
                    PoLineSpec('COFF-DEC-01', '90', '11.25', 170, 'DEC-SW-2417A'),
                    PoLineSpec('COFF-DEC-01', '60', '11.40', 165, 'DEC-SW-2417B'),
                ],
                'confirm',
                (0, 13),
            ),
            (
                'PO-018 — Monsoon Syrups (chai & cold brew)',
                [
                    PoLineSpec('BEV-CHAI-01', '50', '4.55', 115, 'CHAI-CON-2418A'),
                    PoLineSpec('BEV-CHAI-01', '30', '4.60', 105, 'CHAI-CON-2418B'),
                    PoLineSpec('BEV-CBR-01', '45', '6.10', 88, 'CBR-CON-2418A'),
                    PoLineSpec('BEV-CBR-01', '35', '6.15', 82, 'CBR-CON-2418B'),
                ],
                'confirm',
                (0, 20),
            ),
        ]

        for entry in purchase_orders:
            title, lines, action, activity_when = self._unpack_po_seed(entry)
            po = self._create_po(user, catalog, title, lines, today)
            if action == 'confirm':
                confirm_purchase_order(po)
                if activity_when is not None:
                    self._backdate_purchase_order_movements(po, activity_when)
            elif action == 'confirm_cancel':
                confirm_purchase_order(po)
                cancel_purchase_order(po)
                if activity_when is not None:
                    self._backdate_purchase_order_movements(po, activity_when)
            elif action == 'cancel':
                cancel_purchase_order(po)

        self.stdout.write(f'Processed {len(purchase_orders)} purchase orders')

    def _seed_ledger_void_examples(self, user, catalog: dict[str, Product]) -> None:
        """Manual batch void for Stock History demos (VOID movement + voided_at)."""
        product = catalog['SUP-PRO-01']
        stock = Stock.objects.create(
            user=user,
            product=product,
            lot_code='PRO-MANUAL-VOID',
            initial_quantity=Decimal('5'),
            current_quantity=Decimal('0'),
            unit_cost=Decimal('18.50'),
        )
        record_movement(
            user=user,
            stock_batch=stock,
            delta=Decimal('5'),
            reason=MovementReason.RECEIPT,
        )
        void_manual_stock_batch(user=user, stock_batch=stock)

        when = self._activity_timestamp(0, 18)
        StockMovement.objects.filter(stock_batch=stock).update(created_at=when)
        self.stdout.write('Seeded manual batch void example (SUP-PRO-01)')

    def _seed_sales_orders(self, user, catalog: dict[str, Product]):
        sales_orders: list[SoSeedEntry] = [
            (
                'SO-001 — Sunrise Café (weekly restock)',
                [
                    SoLineSpec('COFF-ESP-01', '50', '24.00'),
                    SoLineSpec('DAIR-OAT-01', '30', '3.80'),
                    SoLineSpec('SUP-FLT-04', '200', '0.25'),
                ],
                'confirm',
                (3, 10),
            ),
            (
                'SO-002 — Metro Coffee Roasters (wholesale)',
                [
                    SoLineSpec('COFF-ESP-01', '120', '22.50'),
                    SoLineSpec('COFF-DEC-01', '40', '21.00'),
                ],
                'confirm',
                (3, 18),
            ),
            (
                'SO-003 — Green Leaf Tea House',
                [
                    SoLineSpec('TEA-MAT-01', '2500', '0.18'),
                    SoLineSpec('BEV-CHAI-01', '40', '9.50'),
                    SoLineSpec('SYRP-HON-01', '10', '16.00'),
                ],
                'confirm',
                (2, 9),
            ),
            (
                'SO-004 — Urban Corner Markets (3-store drop)',
                [
                    SoLineSpec('BEV-KMB-01', '180', '3.75'),
                    SoLineSpec('SUP-CUP-12', '600', '0.18'),
                    SoLineSpec('SUP-LID-01', '600', '0.12'),
                ],
                'confirm',
                (2, 17),
            ),
            (
                'SO-005 — The Daily Grind Hotel Group',
                [
                    SoLineSpec('BEV-CBR-01', '80', '14.00'),
                    SoLineSpec('DAIR-OAT-01', '100', '3.60'),
                    SoLineSpec('SUP-CUP-12', '1200', '0.17'),
                    SoLineSpec('SUP-LID-01', '1200', '0.11'),
                ],
                'confirm',
                (2, 24),
            ),
            (
                'SO-006 — Riverside Bakery (ingredients)',
                [
                    SoLineSpec('SPIC-CIN-01', '5000', '0.035'),
                    SoLineSpec('SYRP-HON-01', '8', '15.50'),
                    SoLineSpec('SYRP-VAN-01', '3000', '0.025'),
                    SoLineSpec('BAKE-COC-01', '25', '14.00'),
                ],
                'confirm',
                (1, 6),
            ),
            (
                'SO-007 — Ferment & Fizz (kombucha clearance — near expiry)',
                [
                    SoLineSpec('BEV-KMB-01', '200', '0.95'),
                ],
                'confirm',
                (1, 11),
            ),
            (
                'SO-008 — Campus Food Co. (decaf intro pricing)',
                [
                    SoLineSpec('COFF-DEC-01', '35', '11.00'),
                ],
                'confirm',
                (1, 16),
            ),
            (
                'SO-009 — Pacific Coast Distributors (bulk espresso)',
                [
                    SoLineSpec('COFF-ESP-01', '350', '21.50'),
                ],
                'confirm',
                (1, 21),
            ),
            (
                'SO-010 — West End Café (mixed pantry)',
                [
                    SoLineSpec('DAIR-ALM-01', '60', '3.40'),
                    SoLineSpec('DAIR-CRM-01', '8000', '0.006'),
                    SoLineSpec('SYRP-VAN-01', '2000', '0.022'),
                ],
                'confirm',
                (1, 26),
            ),
            (
                'SO-011 — Artisan Latte Bar',
                [
                    SoLineSpec('TEA-MAT-01', '1500', '0.20'),
                    SoLineSpec('DAIR-OAT-01', '45', '3.90'),
                    SoLineSpec('SUP-FLT-04', '500', '0.22'),
                ],
                'confirm',
                (1, 8),
            ),
            (
                'SO-012 — Marina Deli (retail grab-and-go)',
                [
                    SoLineSpec('BEV-KMB-01', '96', '3.50'),
                    SoLineSpec('BEV-CBR-01', '20', '15.00'),
                ],
                'confirm',
                (1, 14),
            ),
            (
                'SO-013 — Spring Tasting Event (catering)',
                [
                    SoLineSpec('BEV-CHAI-01', '25', '10.00'),
                    SoLineSpec('BAKE-COC-01', '15', '13.50'),
                    SoLineSpec('SUP-CUP-12', '400', '0.16'),
                ],
                'confirm',
                (0, 4),
            ),
            (
                'SO-014 — Office Pantry Refill — FinTech HQ',
                [
                    SoLineSpec('DAIR-ALM-01', '80', '3.25'),
                    SoLineSpec('SUP-FLT-04', '300', '0.20'),
                    SoLineSpec('SUP-LID-01', '400', '0.10'),
                ],
                'confirm',
                (0, 10),
            ),
            (
                'SO-015 — Wholesale deal fell through (cancelled after ship)',
                [
                    SoLineSpec('COFF-ESP-01', '180', '23.00'),
                ],
                'cancel',
                (1, 20),
            ),
            (
                'SO-016 — Weekend Farmers Market pop-up',
                [
                    SoLineSpec('BEV-KMB-01', '48', '4.00'),
                    SoLineSpec('SYRP-HON-01', '3', '18.00'),
                ],
                'confirm',
                (0, 16),
            ),
            (
                'SO-019 — Co-op end-of-line (coconut sugar write-down)',
                [
                    SoLineSpec('BAKE-CNS-01', '40', '3.00'),
                ],
                'confirm',
                (0, 22),
            ),
            (
                'SO-017 — Draft — Q2 contract renewal (Sunrise Café)',
                [
                    SoLineSpec('COFF-ESP-01', '80', '24.00'),
                    SoLineSpec('DAIR-OAT-01', '50', '3.75'),
                ],
                'draft',
            ),
            (
                'SO-018 — Draft — Airport kiosk quote',
                [
                    SoLineSpec('BEV-CBR-01', '60', '13.50'),
                    SoLineSpec('SUP-CUP-12', '2000', '0.15'),
                    SoLineSpec('SUP-LID-01', '2000', '0.09'),
                ],
                'draft',
            ),
        ]

        for entry in sales_orders:
            title, lines, action, activity_when = self._unpack_so_seed(entry)
            so = self._create_so(user, catalog, title, lines)
            if action == 'confirm':
                confirm_sales_order(so)
                if activity_when is not None:
                    self._backdate_sales_order_movements(so, activity_when)
            elif action == 'cancel':
                confirm_sales_order(so)
                cancel_sales_order(so)
                if activity_when is not None:
                    self._backdate_sales_order_movements(so, activity_when)

        self.stdout.write(f'Processed {len(sales_orders)} sales orders')

    @staticmethod
    def _unpack_po_seed(entry: PoSeedEntry) -> tuple[str, list[PoLineSpec], PoAction, Optional[ActivityWhen]]:
        if len(entry) == 4:
            return entry[0], entry[1], entry[2], entry[3]
        return entry[0], entry[1], entry[2], None

    @staticmethod
    def _unpack_so_seed(entry: SoSeedEntry) -> tuple[str, list[SoLineSpec], SoAction, Optional[ActivityWhen]]:
        if len(entry) == 4:
            return entry[0], entry[1], entry[2], entry[3]
        return entry[0], entry[1], entry[2], None

    @staticmethod
    def _activity_timestamp(months_ago: int, day: int) -> datetime:
        today = timezone.localdate()
        month = today.month - months_ago
        year = today.year
        while month <= 0:
            month += 12
            year -= 1

        max_day = calendar.monthrange(year, month)[1]
        if months_ago == 0:
            day = min(day, today.day)
        day = min(max(day, 1), max_day)

        activity_date = date(year, month, day)
        tz = timezone.get_current_timezone()
        return timezone.make_aware(datetime.combine(activity_date, time(12, 0)), tz)

    def _backdate_purchase_order_movements(self, order: PurchaseOrder, activity_when: ActivityWhen) -> None:
        when = self._activity_timestamp(*activity_when)
        StockMovement.objects.filter(
            purchase_order_item__order=order,
            reason__in=[MovementReason.RECEIPT, MovementReason.RECEIPT_REVERSAL],
        ).update(created_at=when)

    def _backdate_sales_order_movements(self, order: SalesOrder, activity_when: ActivityWhen) -> None:
        when = self._activity_timestamp(*activity_when)
        StockMovement.objects.filter(
            sales_order_item__order=order,
            reason__in=[MovementReason.SALE, MovementReason.RETURN],
        ).update(created_at=when)

    def _create_po(
        self,
        user,
        catalog: dict[str, Product],
        title: str,
        lines: list[PoLineSpec],
        today,
    ) -> PurchaseOrder:
        po = PurchaseOrder.objects.create(user=user, title=title)
        for line in lines:
            best_before = (
                today + timedelta(days=line.best_before_days)
                if line.best_before_days is not None
                else None
            )
            PurchaseOrderItem.objects.create(
                order=po,
                product=catalog[line.sku],
                quantity=Decimal(line.quantity),
                unit_cost=Decimal(line.unit_cost),
                lot_code=line.lot_code,
                best_before=best_before,
            )
        return po

    def _create_so(
        self,
        user,
        catalog: dict[str, Product],
        title: str,
        lines: list[SoLineSpec],
    ) -> SalesOrder:
        so = SalesOrder.objects.create(user=user, title=title)
        for line in lines:
            SalesOrderItem.objects.create(
                order=so,
                product=catalog[line.sku],
                quantity=Decimal(line.quantity),
                unit_price=Decimal(line.unit_price),
            )
        return so

    def _print_credentials(self):
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 52))
        self.stdout.write(self.style.SUCCESS('  Demo account — log in to explore the app'))
        self.stdout.write(self.style.SUCCESS('=' * 52))
        self.stdout.write(f'  Email:    {DEMO_EMAIL}')
        self.stdout.write(self.style.SUCCESS('=' * 52))
        self.stdout.write('')

    def _print_summary(self, catalog: dict[str, Product]):
        self.stdout.write('Demo highlights:')
        self.stdout.write(f'  • {len(catalog)} products across KG, G, L, mL, and UNIT')
        self.stdout.write('  • Multi-batch FIFO: most SKUs have 2–6 lots at varied costs and best-before dates')
        self.stdout.write('  • Espresso flagship: older lots at $12.00/kg, restocks at $14.50–14.75/kg')
        self.stdout.write('  • Dashboard mix: strong margins, low-margin decaf intro, loss-leader kombucha clearance')
        self.stdout.write('  • Zero-sales SKUs: Protein Powder, Sparkling Water (stock on hand)')
        self.stdout.write('  • Loss-leader SKU: Coconut Sugar (sold below cost in SO-019)')
        self.stdout.write('  • Sold-out SKU: Cinnamon (filter "Out of stock only" to verify)')
        self.stdout.write('  • Draft PO/SO and cancelled orders for workflow demos')
        self.stdout.write('  • Stock History: filter “Batch voided” (manual SUP-PRO-01) or “Receipt reversed” (PO-009)')
        self.stdout.write('  • Financial period presets: activity spread across ~3 months (try This month / Last month on dashboard)')
        self.stdout.write('')
