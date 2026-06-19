import pytest
from django.urls import reverse
from rest_framework import status
from .models import User


@pytest.mark.django_db
class TestAuthentication:
    def setup_method(self):
        self.register_url = reverse('auth_register')
        self.login_url = reverse('token_obtain_pair')
        self.me_url = reverse('auth_me')
        self.user_data = {
            'email': 'test@example.com',
            'password': 'testpassword123',
        }

    def test_user_registration(self, client):
        response = client.post(self.register_url, self.user_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email='test@example.com').exists()

    def test_duplicate_email_rejected(self, client):
        User.objects.create_user(username='test@example.com', **self.user_data)
        response = client.post(self.register_url, self.user_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_success(self, client):
        User.objects.create_user(username='test@example.com', **self.user_data)
        response = client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'testpassword123',
        })
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_login_invalid_credentials(self, client):
        User.objects.create_user(username='test@example.com', **self.user_data)
        response = client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'wrongpassword',
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_unauthenticated(self, client):
        response = client.get(self.me_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_authenticated(self, client):
        User.objects.create_user(username='test@example.com', **self.user_data)
        login_response = client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'testpassword123',
        })
        token = login_response.data['access']

        response = client.get(self.me_url, HTTP_AUTHORIZATION=f'Bearer {token}')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == 'test@example.com'
