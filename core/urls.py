"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .views import SimpleLogoutView, AuthMeView

urlpatterns = [
    # Redirect root to API documentation
    path('', RedirectView.as_view
         (url='/api/docs/', permanent=False), name='home'),

    path('admin/', admin.site.urls),

    # API v1 - Current stable version
    # Versionamento permite evoluir API sem quebrar clientes existentes
    # Ex futuro: path('api/v2/', include('contracts.urls_v2'))
    path('api/v1/', include('contracts.urls')),
    path('api/v1/auth/me/', AuthMeView.as_view(), name='auth_me'),

    # enable login/logout views for DRF browsable API
    path(
        'api-auth/',
        include('rest_framework.urls', namespace='rest_framework')
    ),
    # JWT endpoints (for SPA/mobile frontends)
    path('api/token/', TokenObtainPairView.as_view
         (), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(),
         name='token_refresh'),
    path(
        'api/token/verify/',
        TokenVerifyView.as_view(),
        name='token_verify',
    ),
    # Custom logout that works with GET (redirects to Swagger)
    path(
        'logout/',
        SimpleLogoutView.as_view(),
        name='logout'
    ),
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui'
    ),
    path(
        'api/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc'
    ),
]
