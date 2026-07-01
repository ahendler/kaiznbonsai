import pytest
from django.test import Client, override_settings


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=['localhost'])
def test_disallowed_host_returns_400():
    client = Client()
    response = client.get('/api/v1/auth/me/', HTTP_HOST='evil.example.com')
    assert response.status_code == 400


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=['localhost'])
def test_allowed_host_is_accepted():
    client = Client()
    response = client.get('/api/v1/auth/me/', HTTP_HOST='localhost')
    assert response.status_code == 401  # unauthenticated, not DisallowedHost
