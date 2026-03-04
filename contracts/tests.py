import pytest
from django.contrib.auth.models import User, Group
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from contracts.models import Contract, Measurement, Payment


# API Base URL - versioned endpoints
API_BASE = '/api/v1'


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def create_groups(db):
    """Create all required groups"""
    admin_group = Group.objects.create(name='ADMIN')
    gestor_group = Group.objects.create(name='GESTOR')
    fornecedor_group = Group.objects.create(name='FORNECEDOR')
    financeiro_group = Group.objects.create(name='FINANCEIRO')
    return {
        'admin': admin_group,
        'gestor': gestor_group,
        'fornecedor': fornecedor_group,
        'financeiro': financeiro_group
    }


@pytest.fixture
def admin_user(db, create_groups):
    """Create admin user"""
    user = User.objects.create_user(
        username='admin',
        password='admin123',
        is_superuser=True,
        is_staff=True
    )
    user.groups.add(create_groups['admin'])
    return user


@pytest.fixture
def gestor_user(db, create_groups):
    """Create gestor user"""
    user = User.objects.create_user(
        username='gestor1',
        password='gestor123'
    )
    user.groups.add(create_groups['gestor'])
    return user


@pytest.fixture
def fornecedor_user(db, create_groups):
    """Create fornecedor user"""
    user = User.objects.create_user(
        username='fornecedor1',
        password='fornecedor123'
    )
    user.groups.add(create_groups['fornecedor'])
    return user


@pytest.fixture
def financeiro_user(db, create_groups):
    """Create financeiro user"""
    user = User.objects.create_user(
        username='financeiro1',
        password='financeiro123'
    )
    user.groups.add(create_groups['financeiro'])
    return user


@pytest.fixture
def contract(db, gestor_user):
    """Create a test contract"""
    return Contract.objects.create(
        title='Test Contract',
        description='Test Description',
        total_value=Decimal('10000.00'),
        remaining_balance=Decimal('10000.00'),
        start_date='2026-01-01',
        end_date='2026-12-31',
        status='ACTIVE',
        manager=gestor_user
    )


@pytest.fixture
def measurement(db, contract, gestor_user):
    """Create a test measurement"""
    return Measurement.objects.create(
        contract=contract,
        value=Decimal('5000.00'),
        description='Test Measurement',
        created_by=gestor_user,
        status='PENDING'
    )


@pytest.fixture
def approved_measurement(db, contract, gestor_user):
    """Create an approved measurement"""
    return Measurement.objects.create(
        contract=contract,
        value=Decimal('3000.00'),
        description='Approved Measurement',
        created_by=gestor_user,
        status='APPROVED'
    )


# Contract Tests
@pytest.mark.django_db
class TestContractAPI:
    """Test Contract CRUD and actions"""

    def test_create_contract_as_gestor(
        self, api_client, gestor_user
    ):
        """Gestor can create contract"""
        api_client.force_authenticate(user=gestor_user)
        data = {
            'title': 'New Contract',
            'description': 'New Description',
            'total_value': '15000.00',
            'start_date': '2026-02-01',
            'end_date': '2026-12-31',
            'status': 'ACTIVE'
        }
        response = api_client.post(f'{API_BASE}/contracts/', data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'New Contract'
        assert (
            Decimal(response.data['remaining_balance']) ==
            Decimal('15000.00')
        )

    def test_create_contract_invalid_dates(
        self, api_client, gestor_user
    ):
        """Cannot create contract with end_date < start_date"""
        api_client.force_authenticate(user=gestor_user)
        data = {
            'title': 'Invalid Contract',
            'description': 'Invalid dates',
            'total_value': '10000.00',
            'start_date': '2026-12-31',
            'end_date': '2026-01-01',
            'status': 'ACTIVE'
        }
        response = api_client.post(f'{API_BASE}/contracts/', data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'end_date' in str(response.data)

    def test_create_contract_invalid_remaining_balance(
        self, api_client, gestor_user
    ):
        """Cannot create contract with remaining_balance > total_value"""
        api_client.force_authenticate(user=gestor_user)
        data = {
            'title': 'Invalid Contract',
            'description': 'Invalid balance',
            'total_value': '10000.00',
            'remaining_balance': '15000.00',
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'status': 'ACTIVE'
        }
        response = api_client.post(f'{API_BASE}/contracts/', data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'remaining_balance' in str(response.data)

    def test_close_contract(self, api_client, gestor_user, contract):
        """Gestor can close their contract"""
        api_client.force_authenticate(user=gestor_user)
        response = api_client.post(
            f'{API_BASE}/contracts/{contract.id}/close/'
        )
        assert response.status_code == status.HTTP_200_OK
        contract.refresh_from_db()
        assert contract.status == 'CLOSED'

    def test_fornecedor_cannot_create_contract(
        self, api_client, fornecedor_user
    ):
        """Fornecedor cannot create contract"""
        api_client.force_authenticate(user=fornecedor_user)
        data = {
            'title': 'Forbidden Contract',
            'description': 'Should fail',
            'total_value': '10000.00',
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'status': 'ACTIVE'
        }
        response = api_client.post(f'{API_BASE}/contracts/', data)
        assert response.status_code == status.HTTP_403_FORBIDDEN


# Measurement Tests
@pytest.mark.django_db
class TestMeasurementAPI:
    """Test Measurement CRUD and actions"""

    def test_create_measurement(
        self, api_client, gestor_user, contract
    ):
        """Gestor can create measurement for their contract"""
        api_client.force_authenticate(user=gestor_user)
        data = {
            'contract': contract.id,
            'value': '4000.00',
            'description': 'Test Measurement'
        }
        response = api_client.post(f'{API_BASE}/measurements/', data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Decimal(response.data['value']) == Decimal('4000.00')
        assert response.data['status'] == 'PENDING'

    def test_create_measurement_zero_value(
        self, api_client, gestor_user, contract
    ):
        """Cannot create measurement with value <= 0"""
        api_client.force_authenticate(user=gestor_user)
        data = {
            'contract': contract.id,
            'value': '0.00',
            'description': 'Invalid Measurement'
        }
        response = api_client.post(f'{API_BASE}/measurements/', data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'value' in str(response.data)

    def test_gestor_cannot_create_measurement_on_other_contract(
        self, api_client, gestor_user, contract
    ):
        """Gestor cannot create measurement on contract he doesn't manage"""
        # Create another gestor and contract managed by him
        other_gestor = User.objects.create_user(
            username='gestor2',
            password='gestor123'
        )
        other_gestor.groups.add(
            Group.objects.get(name='GESTOR')
        )
        other_contract = Contract.objects.create(
            title='Other Contract',
            description='Managed by other gestor',
            total_value=Decimal('10000.00'),
            remaining_balance=Decimal('10000.00'),
            start_date='2026-01-01',
            end_date='2026-12-31',
            status='ACTIVE',
            manager=other_gestor
        )

        # gestor_user tries to create measurement on other_contract
        api_client.force_authenticate(user=gestor_user)
        data = {
            'contract': other_contract.id,
            'value': '1000.00',
            'description': 'Should fail'
        }
        response = api_client.post(f'{API_BASE}/measurements/', data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'manager' in str(response.data).lower()

    def test_create_measurement_on_closed_contract(
        self, api_client, gestor_user, contract
    ):
        """Cannot create measurement on closed contract"""
        contract.status = 'CLOSED'
        contract.save()
        api_client.force_authenticate(user=gestor_user)
        data = {
            'contract': contract.id,
            'value': '1000.00',
            'description': 'Should fail'
        }
        response = api_client.post(f'{API_BASE}/measurements/', data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'closed' in str(response.data).lower()

    def test_approve_measurement(
        self, api_client, gestor_user, measurement
    ):
        """Gestor can approve measurement"""
        api_client.force_authenticate(user=gestor_user)
        response = api_client.post(
            f'{API_BASE}/measurements/{measurement.id}/approve/'
        )
        assert response.status_code == status.HTTP_200_OK

    def test_reject_measurement(
        self, api_client, gestor_user, measurement
    ):
        """Gestor can reject measurement"""
        api_client.force_authenticate(user=gestor_user)
        response = api_client.post(
            f'{API_BASE}/measurements/{measurement.id}/reject/'
        )
        assert response.status_code == status.HTTP_200_OK
        measurement.refresh_from_db()
        assert measurement.status == 'REJECTED'
        assert measurement.rejected_at is not None

    def test_fornecedor_cannot_approve_measurement(
        self, api_client, fornecedor_user, measurement
    ):
        """Fornecedor cannot approve measurement"""
        api_client.force_authenticate(user=fornecedor_user)
        response = api_client.post(
            f'{API_BASE}/measurements/{measurement.id}/approve/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_edit_approved_measurement(
        self, api_client, gestor_user, approved_measurement
    ):
        """Approved measurement cannot be edited"""
        api_client.force_authenticate(user=gestor_user)
        data = {
            'description': 'Should not update',
            'value': '9999.99',
        }
        response = api_client.patch(
            f'{API_BASE}/measurements/{approved_measurement.id}/',
            data
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        approved_measurement.refresh_from_db()
        assert approved_measurement.description == 'Approved Measurement'
        assert approved_measurement.value == Decimal('3000.00')

    def test_cannot_edit_rejected_measurement(
        self, api_client, gestor_user, contract
    ):
        """Rejected measurement cannot be edited"""
        rejected_measurement = Measurement.objects.create(
            contract=contract,
            value=Decimal('2500.00'),
            description='Rejected Measurement',
            created_by=gestor_user,
            status='REJECTED'
        )

        api_client.force_authenticate(user=gestor_user)
        data = {
            'description': 'Should not update',
            'value': '8888.88',
        }
        response = api_client.patch(
            f'{API_BASE}/measurements/{rejected_measurement.id}/',
            data
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        rejected_measurement.refresh_from_db()
        assert rejected_measurement.description == 'Rejected Measurement'
        assert rejected_measurement.value == Decimal('2500.00')

    def test_can_delete_pending_measurement(
        self, api_client, gestor_user, measurement
    ):
        """Pending measurement can be deleted"""
        api_client.force_authenticate(user=gestor_user)
        response = api_client.delete(
            f'{API_BASE}/measurements/{measurement.id}/'
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Measurement.objects.filter(id=measurement.id).exists()

    def test_cannot_delete_approved_measurement(
        self, api_client, gestor_user, approved_measurement
    ):
        """Approved measurement cannot be deleted"""
        api_client.force_authenticate(user=gestor_user)
        response = api_client.delete(
            f'{API_BASE}/measurements/{approved_measurement.id}/'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Measurement.objects.filter(id=approved_measurement.id).exists()

    def test_cannot_delete_rejected_measurement(
        self, api_client, gestor_user, contract
    ):
        """Rejected measurement cannot be deleted"""
        rejected_measurement = Measurement.objects.create(
            contract=contract,
            value=Decimal('1500.00'),
            description='Rejected Measurement',
            created_by=gestor_user,
            status='REJECTED'
        )

        api_client.force_authenticate(user=gestor_user)
        response = api_client.delete(
            f'{API_BASE}/measurements/{rejected_measurement.id}/'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Measurement.objects.filter(id=rejected_measurement.id).exists()


# Payment Tests
@pytest.mark.django_db
class TestPaymentAPI:
    """Test Payment CRUD and actions"""

    def test_cannot_create_payment_manually(
        self, api_client, financeiro_user, approved_measurement
    ):
        """Manual payment creation is blocked"""
        api_client.force_authenticate(user=financeiro_user)
        data = {
            'measurement': approved_measurement.id,
            'amount': '3000.00'
        }
        response = api_client.post(f'{API_BASE}/payments/', data)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_approve_measurement_creates_payment(
        self, api_client, gestor_user, measurement
    ):
        """Approving measurement generates pending payment automatically"""
        api_client.force_authenticate(user=gestor_user)
        response = api_client.post(
            f'{API_BASE}/measurements/{measurement.id}/approve/'
        )
        assert response.status_code == status.HTTP_200_OK

        payment = Payment.objects.get(measurement=measurement)
        assert payment.contract == measurement.contract
        assert payment.amount == measurement.value
        assert payment.status == 'PENDING'

    def test_mark_payment_as_paid(
        self, api_client, financeiro_user, approved_measurement
    ):
        """Financeiro can mark payment as paid"""
        payment = Payment.objects.create(
            measurement=approved_measurement,
            contract=approved_measurement.contract,
            created_by=financeiro_user,
            amount=Decimal('3000.00'),
            status='PENDING'
        )
        contract = approved_measurement.contract
        initial_balance = contract.remaining_balance

        api_client.force_authenticate(user=financeiro_user)
        response = api_client.post(
            f'{API_BASE}/payments/{payment.id}/mark-as-paid/'
        )
        assert response.status_code == status.HTTP_200_OK
        payment.refresh_from_db()
        assert payment.status == 'PAID'
        assert payment.paid_at is not None

        # OBS: O saldo NÃO muda aqui porque já foi decrementado na
        # aprovação da medição. O pagamento apenas muda o status.
        contract.refresh_from_db()
        assert contract.remaining_balance == initial_balance

    def test_mark_payment_as_failed(
        self, api_client, financeiro_user, approved_measurement
    ):
        """Financeiro can mark payment as failed"""
        payment = Payment.objects.create(
            measurement=approved_measurement,
            contract=approved_measurement.contract,
            created_by=financeiro_user,
            amount=Decimal('3000.00'),
            status='PENDING'
        )
        api_client.force_authenticate(user=financeiro_user)
        response = api_client.post(
            f'{API_BASE}/payments/{payment.id}/mark-as-failed/'
        )
        assert response.status_code == status.HTTP_200_OK
        payment.refresh_from_db()
        assert payment.status == 'FAILED'

    def test_fornecedor_cannot_create_payment(
        self, api_client, fornecedor_user, approved_measurement
    ):
        """Fornecedor cannot create payment manually"""
        api_client.force_authenticate(user=fornecedor_user)
        data = {
            'measurement': approved_measurement.id,
            'amount': '1000.00'
        }
        response = api_client.post(f'{API_BASE}/payments/', data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_gestor_cannot_mark_payment_as_paid(
        self, api_client, gestor_user, approved_measurement
    ):
        """Gestor cannot mark payment as paid"""
        payment = Payment.objects.create(
            measurement=approved_measurement,
            contract=approved_measurement.contract,
            created_by=gestor_user,
            amount=Decimal('2000.00'),
            status='PENDING'
        )
        api_client.force_authenticate(user=gestor_user)
        response = api_client.post(
            f'{API_BASE}/payments/{payment.id}/mark-as-paid/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
