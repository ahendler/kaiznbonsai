"""Tests for the /api/v1/auth/register/ endpoint."""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def register_url():
    return reverse('auth_register')


@pytest.mark.django_db
class TestRegistration:
    def test_successful_registration(self, client, register_url):
        payload = {
            'email': 'alice@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        }
        r = client.post(register_url, payload, format='json')
        assert r.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email='alice@example.com').exists()

    def test_duplicate_email_rejected(self, client, register_url):
        User.objects.create_user(
            username='alice', email='alice@example.com', password='StrongPass123!'
        )
        payload = {
            'email': 'alice@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        }
        r = client.post(register_url, payload, format='json')
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_mismatched_passwords_rejected(self, client, register_url):
        payload = {
            'email': 'bob@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'DifferentPass!',
        }
        r = client.post(register_url, payload, format='json')
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password_confirm' in r.data

    def test_weak_password_rejected(self, client, register_url):
        # Django's CommonPasswordValidator should reject this.
        payload = {
            'email': 'carol@example.com',
            'password': 'password',
            'password_confirm': 'password',
        }
        r = client.post(register_url, payload, format='json')
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_password_confirm_rejected(self, client, register_url):
        payload = {
            'email': 'dan@example.com',
            'password': 'StrongPass123!',
        }
        r = client.post(register_url, payload, format='json')
        assert r.status_code == status.HTTP_400_BAD_REQUEST
