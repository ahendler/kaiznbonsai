from django.db.models import F
from rest_framework.pagination import CursorPagination, _reverse_ordering

from apps.inventory.financial_product_filters import parse_ordering


class CreatedAtCursorPagination(CursorPagination):
    ordering = "-created_at"
    page_size = 20


def financial_ordering_with_tiebreaker(field: str) -> tuple[str, str]:
    """Stable string ordering for cursor position encoding."""
    if field.startswith('-'):
        return (field, '-id')
    return (field, 'id')


def financial_sql_ordering(field: str, *, reverse: bool = False) -> tuple:
    """SQL ORDER BY args; markup uses NULLS LAST via F expressions."""
    if field == '-markup_on_cost':
        if reverse:
            return (F('markup_on_cost').asc(nulls_last=True), F('id').asc())
        return (F('markup_on_cost').desc(nulls_last=True), F('id').desc())
    if field == 'markup_on_cost':
        if reverse:
            return (F('markup_on_cost').desc(nulls_last=True), F('id').desc())
        return (F('markup_on_cost').asc(nulls_last=True), F('id').asc())
    ordering = financial_ordering_with_tiebreaker(field)
    if reverse:
        return _reverse_ordering(ordering)
    return ordering


class ProductFinancialsCursorPagination(CursorPagination):
    page_size = 20

    def get_ordering(self, request, queryset, view):
        field = parse_ordering(request.query_params.get('ordering'))
        return financial_ordering_with_tiebreaker(field)

    def paginate_queryset(self, queryset, request, view=None):
        # Mirrors CursorPagination.paginate_queryset (DRF 3.17) with nulls_last SQL for markup.
        self.request = request
        self.page_size = self.get_page_size(request)
        if not self.page_size:
            return None

        self.base_url = request.build_absolute_uri()
        field = parse_ordering(request.query_params.get('ordering'))
        self.ordering = financial_ordering_with_tiebreaker(field)

        self.cursor = self.decode_cursor(request)
        if self.cursor is None:
            (offset, reverse, current_position) = (0, False, None)
        else:
            (offset, reverse, current_position) = self.cursor

        queryset = queryset.order_by(*financial_sql_ordering(field, reverse=reverse))

        if current_position is not None:
            order = self.ordering[0]
            is_reversed = order.startswith('-')
            order_attr = order.lstrip('-')

            if self.cursor.reverse != is_reversed:
                kwargs = {order_attr + '__lt': current_position}
            else:
                kwargs = {order_attr + '__gt': current_position}

            queryset = queryset.filter(**kwargs)

        results = list(queryset[offset:offset + self.page_size + 1])
        self.page = list(results[:self.page_size])

        if len(results) > len(self.page):
            has_following_position = True
            following_position = self._get_position_from_instance(results[-1], self.ordering)
        else:
            has_following_position = False
            following_position = None

        if reverse:
            self.page = list(reversed(self.page))
            self.has_next = (current_position is not None) or (offset > 0)
            self.has_previous = has_following_position
            if self.has_next:
                self.next_position = current_position
            if self.has_previous:
                self.previous_position = following_position
        else:
            self.has_next = has_following_position
            self.has_previous = (current_position is not None) or (offset > 0)
            if self.has_next:
                self.next_position = following_position
            if self.has_previous:
                self.previous_position = current_position

        if (self.has_previous or self.has_next) and self.template is not None:
            self.display_page_controls = True

        return self.page


class StockMovementCursorPagination(CursorPagination):
    page_size = 20
    ordering = ('-created_at', '-id')
