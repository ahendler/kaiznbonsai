from rest_framework.pagination import CursorPagination

from apps.inventory.financial_product_filters import parse_ordering


class CreatedAtCursorPagination(CursorPagination):
    ordering = "-created_at"
    page_size = 20


def financial_ordering_with_tiebreaker(field: str) -> tuple[str, str]:
    """Stable cursor pagination requires a unique ordering."""
    if field.startswith('-'):
        return (field, '-id')
    return (field, 'id')


class ProductFinancialsCursorPagination(CursorPagination):
    page_size = 20

    def get_ordering(self, request, queryset, view):
        field = parse_ordering(request.query_params.get('ordering'))
        return financial_ordering_with_tiebreaker(field)
