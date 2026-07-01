import pytest
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum

from apps.accounts.models import User
from apps.inventory.commands import record_movement, void_manual_stock_batch
from apps.inventory.models import MovementReason, Product, Stock, StockMovement
from apps.orders.commands import confirm_purchase_order, create_purchase_order


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='ledger_user',
        email='ledger@example.com',
        password='password',
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username='other_user',
        email='other@example.com',
        password='password',
    )


@pytest.fixture
def product(user):
    return Product.objects.create(
        user=user,
        name='Espresso',
        sku='ESP-001',
        unit_of_measure='KG',
    )


@pytest.fixture
def stock_batch(user, product):
    return Stock.objects.create(
        user=user,
        product=product,
        lot_code='LOT-1',
        initial_quantity=Decimal('100.000'),
        current_quantity=Decimal('0'),
        unit_cost=Decimal('10.00'),
    )


@pytest.mark.django_db
class TestRecordMovement:
    def test_positive_delta_increments_quantity_and_creates_movement(self, user, stock_batch):
        movement = record_movement(
            user=user,
            stock_batch=stock_batch,
            delta=Decimal('100.000'),
            reason=MovementReason.RECEIPT,
        )

        stock_batch.refresh_from_db()
        assert movement.reason == MovementReason.RECEIPT
        assert movement.delta == Decimal('100.000')
        assert stock_batch.current_quantity == Decimal('100.000')
        assert StockMovement.objects.filter(stock_batch=stock_batch).count() == 1

    def test_negative_delta_decrements_quantity_and_creates_movement(self, user, stock_batch):
        record_movement(
            user=user,
            stock_batch=stock_batch,
            delta=Decimal('50.000'),
            reason=MovementReason.RECEIPT,
        )

        movement = record_movement(
            user=user,
            stock_batch=stock_batch,
            delta=Decimal('-20.000'),
            reason=MovementReason.SALE,
        )

        stock_batch.refresh_from_db()
        assert movement.reason == MovementReason.SALE
        assert movement.delta == Decimal('-20.000')
        assert stock_batch.current_quantity == Decimal('30.000')

    def test_negative_delta_below_zero_rolls_back(self, user, stock_batch):
        record_movement(
            user=user,
            stock_batch=stock_batch,
            delta=Decimal('10.000'),
            reason=MovementReason.RECEIPT,
        )
        stock_batch.refresh_from_db()

        with pytest.raises(ValidationError, match="cannot be negative"):
            record_movement(
                user=user,
                stock_batch=stock_batch,
                delta=Decimal('-15.000'),
                reason=MovementReason.SALE,
            )

        stock_batch.refresh_from_db()
        assert stock_batch.current_quantity == Decimal('10.000')
        assert StockMovement.objects.filter(stock_batch=stock_batch).count() == 1

    def test_cross_user_call_raises_validation_error(self, user, other_user, stock_batch):
        with pytest.raises(ValidationError, match="not found"):
            record_movement(
                user=other_user,
                stock_batch=stock_batch,
                delta=Decimal('5.000'),
                reason=MovementReason.RECEIPT,
            )

        stock_batch.refresh_from_db()
        assert stock_batch.current_quantity == Decimal('0')
        assert StockMovement.objects.filter(stock_batch=stock_batch).count() == 0

    def test_sum_of_deltas_equals_current_quantity_after_multiple_calls(self, user, stock_batch):
        record_movement(
            user=user,
            stock_batch=stock_batch,
            delta=Decimal('100.000'),
            reason=MovementReason.RECEIPT,
        )
        record_movement(
            user=user,
            stock_batch=stock_batch,
            delta=Decimal('-30.000'),
            reason=MovementReason.SALE,
        )
        record_movement(
            user=user,
            stock_batch=stock_batch,
            delta=Decimal('10.000'),
            reason=MovementReason.ADJUSTMENT,
        )

        stock_batch.refresh_from_db()
        total_delta = stock_batch.movements.aggregate(total=Sum('delta'))['total']
        assert total_delta == stock_batch.current_quantity == Decimal('80.000')


def _fund_manual_batch(stock_batch, user, quantity='25.000'):
    record_movement(
        user=user,
        stock_batch=stock_batch,
        delta=Decimal(quantity),
        reason=MovementReason.RECEIPT,
    )
    stock_batch.refresh_from_db()


@pytest.mark.django_db
class TestVoidManualStockBatch:
    def test_void_appends_movement_and_sets_voided_at(self, user, stock_batch):
        _fund_manual_batch(stock_batch, user)
        movement_count_before = stock_batch.movements.count()

        result = void_manual_stock_batch(user=user, stock_batch=stock_batch)

        result.refresh_from_db()
        assert result.voided_at is not None
        assert result.current_quantity == Decimal('0')
        assert result.movements.count() == movement_count_before + 1

        void_movement = result.movements.get(reason=MovementReason.VOID)
        assert void_movement.delta == Decimal('-25.000')
        assert not result.movements.filter(reason=MovementReason.ADJUSTMENT).exists()

    def test_void_po_linked_batch_raises(self, user, product):
        po = create_purchase_order(
            user,
            [{'product_id': product.id, 'quantity': 10, 'unit_cost': 5.00}],
        )
        confirm_purchase_order(po)
        batch = Stock.objects.get(purchase_order_item__order=po)

        with pytest.raises(ValidationError, match='purchase order'):
            void_manual_stock_batch(user=user, stock_batch=batch)

        batch.refresh_from_db()
        assert batch.voided_at is None
        assert not batch.movements.filter(reason=MovementReason.VOID).exists()

    def test_void_batch_with_sale_history_raises(self, user, stock_batch):
        _fund_manual_batch(stock_batch, user, quantity='100.000')
        record_movement(
            user=user,
            stock_batch=stock_batch,
            delta=Decimal('-10.000'),
            reason=MovementReason.SALE,
        )
        stock_batch.refresh_from_db()

        with pytest.raises(ValidationError, match='sale'):
            void_manual_stock_batch(user=user, stock_batch=stock_batch)

        stock_batch.refresh_from_db()
        assert stock_batch.voided_at is None
        assert not stock_batch.movements.filter(reason=MovementReason.VOID).exists()

    def test_void_already_voided_batch_raises(self, user, stock_batch):
        _fund_manual_batch(stock_batch, user)
        void_manual_stock_batch(user=user, stock_batch=stock_batch)

        with pytest.raises(ValidationError, match='already been voided'):
            void_manual_stock_batch(user=user, stock_batch=stock_batch)

    def test_void_batch_with_no_remaining_quantity_raises(self, user, stock_batch):
        with pytest.raises(ValidationError, match='no remaining quantity'):
            void_manual_stock_batch(user=user, stock_batch=stock_batch)

    def test_void_cross_user_raises(self, user, other_user, stock_batch):
        _fund_manual_batch(stock_batch, user)

        with pytest.raises(ValidationError, match='not found'):
            void_manual_stock_batch(user=other_user, stock_batch=stock_batch)

        stock_batch.refresh_from_db()
        assert stock_batch.voided_at is None
