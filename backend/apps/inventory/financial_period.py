from datetime import date

from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError


def parse_financial_period(
    from_param: str | None,
    to_param: str | None,
) -> tuple[date | None, date | None]:
    """Return (date_from, date_to) for an inclusive period, or (None, None) for all-time."""
    if from_param is None and to_param is None:
        return None, None

    if (from_param is None) != (to_param is None):
        raise ValidationError(
            {'detail': 'Both "from" and "to" query params are required when filtering by period.'}
        )

    date_from = parse_date(from_param)
    date_to = parse_date(to_param)
    if date_from is None or date_to is None:
        raise ValidationError({'detail': 'Invalid date format. Use YYYY-MM-DD.'})

    if date_from > date_to:
        raise ValidationError({'detail': '"from" must be on or before "to".'})

    return date_from, date_to
