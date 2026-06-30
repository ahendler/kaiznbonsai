from django.core.exceptions import ValidationError

from apps.inventory.models import Product

PRODUCT_NOT_FOUND = 'Product not found.'
PRODUCTS_NOT_FOUND = 'One or more selected products were not found.'


def validate_products_belong_to_user(user, product_ids: set[int]) -> None:
    """Ensure every product id belongs to the requesting user."""
    if not product_ids:
        return

    owned_ids = set(
        Product.objects.filter(user=user, id__in=product_ids).values_list('id', flat=True)
    )
    if owned_ids != product_ids:
        raise ValidationError(
            PRODUCT_NOT_FOUND if len(product_ids) == 1 else PRODUCTS_NOT_FOUND
        )
