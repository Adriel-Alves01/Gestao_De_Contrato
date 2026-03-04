import pytest
from django.contrib.auth.models import Group, User
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestAuthMeEndpoint:
    def test_returns_authenticated_user_data(self, api_client):
        gestor_group = Group.objects.create(name='GESTOR')
        user = User.objects.create_user(
            username='user_me',
            password='pass123',
            email='user_me@test.com',
            first_name='User',
            last_name='Me',
        )
        user.groups.add(gestor_group)

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/v1/auth/me/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == user.id
        assert response.data['username'] == 'user_me'
        assert response.data['email'] == 'user_me@test.com'
        assert response.data['first_name'] == 'User'
        assert response.data['last_name'] == 'Me'
        assert response.data['is_superuser'] is False
        assert response.data['groups'] == ['GESTOR']

    def test_rejects_unauthenticated_request(self, api_client):
        response = api_client.get('/api/v1/auth/me/')

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]
