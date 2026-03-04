"""
Custom views for the core app.
"""
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views import View
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class SimpleLogoutView(View):
    """
    Logout view that accepts GET requests and redirects to specified page.

    This is useful for development/testing when you need a simple
    logout link that works in the browser.
    """

    def get(self, request):
        """Handle GET request for logout."""
        logout(request)
        return redirect('/api/docs/')


class AuthMeView(APIView):
    """Retorna dados do usuário autenticado para hidratação do frontend."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        groups = list(user.groups.values_list('name', flat=True))

        return Response(
            {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_superuser': user.is_superuser,
                'groups': groups,
            }
        )
