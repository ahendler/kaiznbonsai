"""Tests for login, token refresh, logout, and /me/ endpoints."""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User

LOGIN_URL = '/api/v1/auth/login/'
REFRESH_URL = '/api/v1/auth/token/refresh/'
LOGOUT_URL = '/api/v1/auth/logout/'
ME_URL = '/api/v1/auth/me/'


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='StrongPass123!',
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    r = client.post(LOGIN_URL, {'email': user.email, 'password': 'StrongPass123!'}, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return client, r


@pytest.mark.django_db
class TestLogin:
    def test_login_returns_access_token_and_user(self, client, user):
        r = client.post(LOGIN_URL, {'email': user.email, 'password': 'StrongPass123!'}, format='json')
        assert r.status_code == status.HTTP_200_OK
        assert 'access' in r.data
        assert 'user' in r.data
        assert r.data['user']['email'] == user.email
        # Refresh token must NOT be in the body — it lives in the httpOnly cookie.
        assert 'refresh' not in r.data

    def test_login_sets_refresh_cookie(self, client, user):
        r = client.post(LOGIN_URL, {'email': user.email, 'password': 'StrongPass123!'}, format='json')
        assert r.status_code == status.HTTP_200_OK
        assert 'refresh_token' in r.cookies

    def test_login_wrong_password_returns_401(self, client, user):
        r = client.post(LOGIN_URL, {'email': user.email, 'password': 'wrongpass'}, format='json')
        assert r.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_unknown_email_returns_401(self, client, db):
        r = client.post(LOGIN_URL, {'email': 'nobody@example.com', 'password': 'StrongPass123!'}, format='json')
        assert r.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestMe:
    def test_me_without_token_returns_401(self, client):
        r = client.get(ME_URL)
        assert r.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_with_valid_token_returns_user(self, auth_client, user):
        client, _ = auth_client
        r = client.get(ME_URL)
        assert r.status_code == status.HTTP_200_OK
        assert r.data['email'] == user.email
        assert r.data['id'] == user.id


@pytest.mark.django_db
class TestLogout:
    def test_logout_returns_204(self, auth_client):
        client, login_response = auth_client
        # Simulate the browser sending back the httpOnly cookie on logout.
        refresh_cookie = login_response.cookies.get('refresh_token')
        if refresh_cookie:
            client.cookies['refresh_token'] = refresh_cookie.value
        r = client.post(LOGOUT_URL)
        assert r.status_code == status.HTTP_204_NO_CONTENT

    def test_logout_without_auth_returns_401(self, client):
        r = client.post(LOGOUT_URL)
        assert r.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestRefresh:
    def test_refresh_via_cookie_returns_access_token(self, client, user):
        login = client.post(
            LOGIN_URL,
            {'email': user.email, 'password': 'StrongPass123!'},
            format='json',
        )
        assert login.status_code == status.HTTP_200_OK
        refresh_cookie = login.cookies.get('refresh_token')
        assert refresh_cookie is not None

        client.cookies['refresh_token'] = refresh_cookie.value
        r = client.post(REFRESH_URL, {}, format='json')
        assert r.status_code == status.HTTP_200_OK
        assert 'access' in r.data
        assert 'refresh' not in r.data
        assert 'refresh_token' in r.cookies

    def test_refresh_without_cookie_returns_401(self, client):
        r = client.post(REFRESH_URL, {}, format='json')
        assert r.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_via_body_without_cookie_returns_401(self, client, user):
        login = client.post(
            LOGIN_URL,
            {'email': user.email, 'password': 'StrongPass123!'},
            format='json',
        )
        refresh_token = login.cookies['refresh_token'].value

        bare_client = APIClient()
        r = bare_client.post(REFRESH_URL, {'refresh': refresh_token}, format='json')
        assert r.status_code == status.HTTP_401_UNAUTHORIZED
