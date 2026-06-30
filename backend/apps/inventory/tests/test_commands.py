import pytest
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum

from apps.accounts.models import User
from apps.inventory.commands import record_movement
from apps.inventory.models import MovementReason, Product, Stock, StockMovement


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
        with pytest.raises(ValidationError, match="does not belong"):
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
