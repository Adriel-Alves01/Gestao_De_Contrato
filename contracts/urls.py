from rest_framework.routers import DefaultRouter
from .views import (
    ContractViewSet,
    MeasurementViewSet,
    PaymentViewSet,
    UserViewSet,
    AuditLogViewSet,
)
from .analytics import AnalyticsViewSet

router = DefaultRouter()
router.register(r'contracts', ContractViewSet, basename='contract')
router.register(r'measurements', MeasurementViewSet, basename='measurement')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'users', UserViewSet, basename='user')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')

urlpatterns = router.urls
