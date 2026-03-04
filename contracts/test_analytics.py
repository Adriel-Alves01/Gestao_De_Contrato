"""
Tests for Analytics and Dashboard endpoints.
"""
import pytest
from decimal import Decimal
from django.contrib.auth.models import User, Group
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APIClient

from contracts.models import Contract, Measurement, Payment, AuditLog


@pytest.fixture
def api_client():
    """API client for requests"""
    return APIClient()


@pytest.fixture
def analytics_setup(db):
    """Setup complete test data for analytics"""
    # Create groups
    admin_group, _ = Group.objects.get_or_create(name='ADMIN')
    gestor_group, _ = Group.objects.get_or_create(name='GESTOR')
    financeiro_group, _ = Group.objects.get_or_create(name='FINANCEIRO')
    fornecedor_group, _ = Group.objects.get_or_create(name='FORNECEDOR')

    # Create users
    admin = User.objects.create_user(
        username='admin_analytics',
        password='pass123',
    )
    admin.groups.add(admin_group)

    gestor1 = User.objects.create_user(
        username='gestor1_analytics',
        password='pass123',
    )
    gestor1.groups.add(gestor_group)

    gestor2 = User.objects.create_user(
        username='gestor2_analytics',
        password='pass123',
    )
    gestor2.groups.add(gestor_group)

    financeiro = User.objects.create_user(
        username='financeiro_analytics',
        password='pass123',
    )
    financeiro.groups.add(financeiro_group)

    fornecedor = User.objects.create_user(
        username='fornecedor_analytics',
        password='pass123',
    )
    fornecedor.groups.add(fornecedor_group)

    # Create contracts
    contract1 = Contract.objects.create(
        title='Contract 1',
        description='Test contract 1',
        total_value=Decimal('100000.00'),
        remaining_balance=Decimal('60000.00'),
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timedelta(days=365),
        status=Contract.Status.ACTIVE,
        manager=gestor1,
    )

    contract2 = Contract.objects.create(
        title='Contract 2',
        description='Test contract 2',
        total_value=Decimal('50000.00'),
        remaining_balance=Decimal('50000.00'),
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timedelta(days=365),
        status=Contract.Status.ACTIVE,
        manager=gestor1,
    )

    contract3 = Contract.objects.create(
        title='Contract 3',
        description='Test contract 3',
        total_value=Decimal('200000.00'),
        remaining_balance=Decimal('50000.00'),
        start_date=timezone.now().date() - timedelta(days=365),
        end_date=timezone.now().date(),
        status=Contract.Status.CLOSED,
        manager=gestor2,
    )

    Contract.objects.filter(id=contract3.id).update(
        created_at=timezone.now() - timedelta(days=400)
    )

    # Create measurements
    measurement1 = Measurement.objects.create(
        contract=contract1,
        created_by=fornecedor,
        description='Measurement 1',
        value=Decimal('40000.00'),
        status=Measurement.Status.APPROVED,
        approved_at=timezone.now(),
    )

    Measurement.objects.create(
        contract=contract1,
        created_by=fornecedor,
        description='Measurement 2',
        value=Decimal('30000.00'),
        status=Measurement.Status.PENDING,
    )

    Measurement.objects.create(
        contract=contract2,
        created_by=fornecedor,
        description='Measurement 3',
        value=Decimal('25000.00'),
        status=Measurement.Status.REJECTED,
        rejected_at=timezone.now(),
    )

    measurement4 = Measurement.objects.create(
        contract=contract3,
        created_by=fornecedor,
        description='Measurement 4',
        value=Decimal('150000.00'),
        status=Measurement.Status.APPROVED,
        approved_at=timezone.now() - timedelta(days=30),
    )

    # Create payments
    Payment.objects.create(
        contract=contract1,
        measurement=measurement1,
        created_by=financeiro,
        amount=Decimal('40000.00'),
        status=Payment.Status.PAID,
        paid_at=timezone.now(),
    )

    Payment.objects.create(
        contract=contract3,
        measurement=measurement4,
        created_by=financeiro,
        amount=Decimal('150000.00'),
        status=Payment.Status.PAID,
        paid_at=timezone.now() - timedelta(days=30),
    )

    # Create audit logs
    AuditLog.objects.create(
        user=gestor1,
        action=AuditLog.Action.CREATE,
        model_name='Contract',
        object_id=contract1.id,
        object_display=contract1.title,
    )

    return {
        'admin': admin,
        'gestor1': gestor1,
        'gestor2': gestor2,
        'financeiro': financeiro,
        'fornecedor': fornecedor,
        'contract1': contract1,
        'contract2': contract2,
        'contract3': contract3,
    }


@pytest.mark.django_db
class TestAnalyticsOverview:
    """Test overview endpoint"""

    def test_admin_can_see_full_overview(self, api_client, analytics_setup):
        """ADMIN sees all contracts in overview"""
        api_client.force_authenticate(user=analytics_setup['admin'])
        response = api_client.get('/api/v1/analytics/overview/')

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Check structure
        assert 'contracts' in data
        assert 'measurements' in data
        assert 'payments' in data
        assert 'recent_activities' in data

        # Check contract metrics (all 3 contracts)
        contracts = data['contracts']
        assert contracts['total_contracts'] == 3
        assert contracts['active_contracts'] == 2
        assert contracts['closed_contracts'] == 1

    def test_gestor_sees_only_own_contracts(self, api_client, analytics_setup):
        """GESTOR sees only their own contracts"""
        api_client.force_authenticate(user=analytics_setup['gestor1'])
        response = api_client.get('/api/v1/analytics/overview/')

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # gestor1 has 2 contracts
        assert data['contracts']['total_contracts'] == 2
        assert data['contracts']['active_contracts'] == 2

    def test_unauthenticated_cannot_access(self, api_client):
        """Unauthenticated users cannot access"""
        response = api_client.get('/api/v1/analytics/overview/')
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]


@pytest.mark.django_db
class TestAnalyticsContracts:
    """Test contracts metrics endpoint"""

    def test_contracts_metrics(self, api_client, analytics_setup):
        """Test contract metrics"""
        api_client.force_authenticate(user=analytics_setup['admin'])
        response = api_client.get('/api/v1/analytics/contracts/')

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert data['total_contracts'] == 3
        assert data['active_contracts'] == 2
        assert data['closed_contracts'] == 1

    def test_contracts_period_month(self, api_client, analytics_setup):
        """Filter contracts metrics by last month"""
        api_client.force_authenticate(user=analytics_setup['admin'])
        response = api_client.get(
            '/api/v1/analytics/contracts/?period=month'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert data['total_contracts'] == 2
        assert data['active_contracts'] == 2
        assert data['closed_contracts'] == 0

    def test_contracts_closed_incomplete(self, api_client, analytics_setup):
        """Filter closed contracts with remaining balance"""
        api_client.force_authenticate(user=analytics_setup['admin'])
        response = api_client.get(
            '/api/v1/analytics/contracts/?closed_incomplete=true'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert data['total_contracts'] == 1
        assert data['active_contracts'] == 0
        assert data['closed_contracts'] == 1


@pytest.mark.django_db
class TestAnalyticsMeasurements:
    """Test measurements metrics endpoint"""

    def test_measurements_metrics(self, api_client, analytics_setup):
        """Test measurement metrics"""
        api_client.force_authenticate(user=analytics_setup['admin'])
        response = api_client.get('/api/v1/analytics/measurements/')

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert data['total_measurements'] == 4
        assert data['pending_measurements'] == 1
        assert data['approved_measurements'] == 2
        assert data['rejected_measurements'] == 1


@pytest.mark.django_db
class TestAnalyticsPayments:
    """Test payments metrics endpoint"""

    def test_payments_metrics(self, api_client, analytics_setup):
        """Test payment metrics"""
        api_client.force_authenticate(user=analytics_setup['admin'])
        response = api_client.get('/api/v1/analytics/payments/')

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert data['total_payments'] == 2
        assert data['paid_payments'] == 2
        assert data['pending_payments'] == 0


@pytest.mark.django_db
class TestAnalyticsByManager:
    """Test by_manager endpoint"""

    def test_by_manager_metrics(self, api_client, analytics_setup):
        """Test metrics grouped by manager"""
        api_client.force_authenticate(user=analytics_setup['admin'])
        response = api_client.get('/api/v1/analytics/by_manager/')

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Should have 2 managers
        assert len(data) == 2

    def test_by_manager_period_month(self, api_client, analytics_setup):
        """Filter by manager metrics for last month"""
        api_client.force_authenticate(user=analytics_setup['admin'])
        response = api_client.get(
            '/api/v1/analytics/by_manager/?period=month'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert len(data) == 1
        assert data[0]['manager_id'] == analytics_setup['gestor1'].id
        assert data[0]['total_contracts'] == 2


@pytest.mark.django_db
class TestAnalyticsFinancial:
    """Test financial summary endpoint"""

    def test_financial_summary(self, api_client, analytics_setup):
        """Test financial summary"""
        api_client.force_authenticate(user=analytics_setup['admin'])
        response = api_client.get('/api/v1/analytics/financial/')

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert 'total_contracted' in data
        assert 'total_measured' in data
        assert 'total_paid' in data
        assert Decimal(data['total_contracted']) == Decimal('350000.00')


@pytest.mark.django_db
class TestAnalyticsTimeline:
    """Test timeline endpoint"""

    def test_timeline_default(self, api_client, analytics_setup):
        """Test timeline with default parameters"""
        api_client.force_authenticate(user=analytics_setup['admin'])
        response = api_client.get('/api/v1/analytics/timeline/')

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert isinstance(data, list)


@pytest.mark.django_db
class TestAnalyticsStatusDistribution:
    """Test status distribution endpoint"""

    def test_contract_status_distribution(self, api_client, analytics_setup):
        """Test contract status distribution"""
        api_client.force_authenticate(user=analytics_setup['admin'])
        response = api_client.get(
            '/api/v1/analytics/status_distribution/?type=contracts'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Should have 2 statuses (ACTIVE and CLOSED)
        assert len(data) == 2

    def test_measurement_status_distribution(
        self, api_client, analytics_setup
    ):
        """Test measurement status distribution"""
        api_client.force_authenticate(user=analytics_setup['admin'])
        response = api_client.get(
            '/api/v1/analytics/status_distribution/?type=measurements'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Should have 3 statuses
        assert len(data) == 3


@pytest.mark.django_db
class TestAnalyticsPermissions:
    """Test permission enforcement"""

    def test_financeiro_can_access(self, api_client, analytics_setup):
        """FINANCEIRO can access analytics"""
        api_client.force_authenticate(user=analytics_setup['financeiro'])
        response = api_client.get('/api/v1/analytics/overview/')

        assert response.status_code == status.HTTP_200_OK
