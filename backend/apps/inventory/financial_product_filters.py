from rest_framework.exceptions import ValidationError

VALID_MARGIN_BANDS = frozenset({'negative', 'low', 'medium', 'high'})
VALID_ACTIVITY_FILTERS = frozenset({'all', 'movement', 'stale'})
VALID_ORDERINGS = frozenset({'-created_at', '-revenue', '-profit', '-margin', 'name'})


def parse_search(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def parse_margin_band(value: str | None) -> str | None:
    if value is None or value == '':
        return None
    if value not in VALID_MARGIN_BANDS:
        raise ValidationError(
            {
                'detail': (
                    'Invalid margin_band. Choose one of: '
                    f'{", ".join(sorted(VALID_MARGIN_BANDS))}.'
                )
            }
        )
    return value


def parse_activity(value: str | None) -> str:
    if value is None or value == '':
        return 'all'
    if value not in VALID_ACTIVITY_FILTERS:
        raise ValidationError(
            {
                'detail': (
                    'Invalid activity. Choose one of: '
                    f'{", ".join(sorted(VALID_ACTIVITY_FILTERS))}.'
                )
            }
        )
    return value


def parse_ordering(value: str | None) -> str:
    if value is None or value == '':
        return '-created_at'
    if value not in VALID_ORDERINGS:
        raise ValidationError(
            {
                'detail': (
                    'Invalid ordering. Choose one of: '
                    f'{", ".join(sorted(VALID_ORDERINGS))}.'
                )
            }
        )
    return value
