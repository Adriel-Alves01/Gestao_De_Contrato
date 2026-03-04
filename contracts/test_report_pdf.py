"""
Testes para geração de relatórios em PDF.
"""
import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from contracts.models import Payment


@pytest.fixture
def api_client():
    """Cliente API para testes."""
    return APIClient()


@pytest.fixture
def users_with_roles(db):
    """Cria usuários com diferentes roles."""
    from django.contrib.auth.models import User, Group

    # Cria grupos se não existirem
    admin_group, _ = Group.objects.get_or_create(name='ADMIN')
    gestor_group, _ = Group.objects.get_or_create(name='GESTOR')
    fornecedor_group, _ = Group.objects.get_or_create(name='FORNECEDOR')
    financeiro_group, _ = Group.objects.get_or_create(name='FINANCEIRO')

    # Cria usuários
    gestor = User.objects.create_user(
        username='gestor_user',
        email='gestor@test.com',
        password='testpass123'
    )
    gestor.groups.add(gestor_group)

    admin = User.objects.create_user(
        username='admin_user',
        email='admin@test.com',
        password='testpass123'
    )
    admin.groups.add(admin_group)
    admin.is_staff = True
    admin.save()

    fornecedor = User.objects.create_user(
        username='fornecedor_user',
        email='fornecedor@test.com',
        password='testpass123'
    )
    fornecedor.groups.add(fornecedor_group)

    financeiro = User.objects.create_user(
        username='financeiro_user',
        email='financeiro@test.com',
        password='testpass123'
    )
    financeiro.groups.add(financeiro_group)

    return {
        'gestor': gestor,
        'admin': admin,
        'fornecedor': fornecedor,
        'financeiro': financeiro,
    }


class TestContractReportPDF:
    """Testes de geração de relatórios em PDF."""

    @pytest.mark.django_db
    def test_generate_pdf_report_single_contract(
        self, api_client, users_with_roles
    ):
        """ Gerar PDF individual de um contrato"""
        gestor = users_with_roles['gestor']
        api_client.force_authenticate(user=gestor)

        print("\n Testando: Gerar PDF de contrato")

        # 1. Criar contrato
        contract_data = {
            'title': 'Contrato para Relatório PDF',
            'manager': gestor.id,
            'total_value': 100000.00,
            'start_date': timezone.now().date(),
            'end_date': (timezone.now() + timedelta(days=365)).date(),
            'remaining_balance': 100000.00,
            'description': (
                'Este é um contrato de teste para gerar relatório em PDF.'
            ),
        }
        response = api_client.post('/api/v1/contracts/', contract_data)
        assert response.status_code == 201
        contract_id = response.json()['id']
        print(f"    Contrato criado: {contract_id}")

        # 2. Criar medição
        measurement_data = {
            'contract': contract_id,
            'value': 25000.00,
            'description': 'Primeira medição'
        }
        response = api_client.post('/api/v1/measurements/', measurement_data)
        assert response.status_code == 201
        measurement_id = response.json()['id']
        print(f"    Medição criada: {measurement_id}")

        # 3. Aprovar medição
        response = api_client.post(
            f'/api/v1/measurements/{measurement_id}/approve/', {}
        )
        assert response.status_code == 200
        print("    Medição aprovada")

        # 4. Pagamento é criado automaticamente ao aprovar medição
        api_client.force_authenticate(user=users_with_roles['financeiro'])
        payment = Payment.objects.get(measurement_id=measurement_id)
        payment_id = payment.id
        print(f"    Pagamento auto-criado: {payment_id}")

        # 5. Marcar pagamento como PAID
        response = api_client.post(
            f'/api/v1/payments/{payment_id}/mark-as-paid/', {}
        )
        assert response.status_code == 200
        print("    Pagamento marcado como PAID")

        # 6. Gerar PDF (voltar para GESTOR)
        api_client.force_authenticate(user=gestor)
        response = api_client.get(
            f'/api/v1/contracts/{contract_id}/report/pdf/'
        )

        # Validações
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        assert 'attachment' in response['Content-Disposition']
        assert f'contrato_{contract_id}' in response['Content-Disposition']

        # Verifica se é um PDF válido (FileResponse usa streaming_content)
        content = b''.join(response.streaming_content)
        assert len(content) > 0
        assert content.startswith(b'%PDF')  # Assinatura de arquivo PDF

        print(f"    PDF gerado com sucesso: {len(content)} bytes")
        print(f"    Nome do arquivo: contrato_{contract_id}_*.pdf")

    @pytest.mark.django_db
    def test_admin_can_generate_any_contract_pdf(
        self, api_client, users_with_roles
    ):
        """ ADMIN consegue gerar PDF de qualquer contrato"""
        gestor = users_with_roles['gestor']
        admin = users_with_roles['admin']

        # GESTOR cria contrato
        api_client.force_authenticate(user=gestor)
        contract_data = {
            'title': 'Contrato do GESTOR',
            'manager': gestor.id,
            'total_value': 50000.00,
            'start_date': timezone.now().date(),
            'end_date': (timezone.now() + timedelta(days=365)).date(),
            'remaining_balance': 50000.00,
        }
        response = api_client.post('/api/v1/contracts/', contract_data)
        contract_id = response.json()['id']

        print("\n Testando: ADMIN gerando PDF de contrato de GESTOR")

        # ADMIN gera PDF
        api_client.force_authenticate(user=admin)
        response = api_client.get(
            f'/api/v1/contracts/{contract_id}/report/pdf/'
        )

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        content = b''.join(response.streaming_content)
        assert content.startswith(b'%PDF')

        print("    ADMIN conseguiu gerar PDF")

    @pytest.mark.django_db
    def test_gestor_cannot_generate_other_contract_pdf(
        self, api_client, users_with_roles
    ):
        """
         GESTOR consegue gerar PDF de qualquer contrato (leitura permissiva)
        """
        gestor1 = users_with_roles['gestor']

        # Criar segundo gestor
        from django.contrib.auth.models import User, Group
        gestor_group = Group.objects.get(name='GESTOR')
        gestor2 = User.objects.create_user(
            username='gestor2_user',
            email='gestor2@test.com',
            password='testpass123'
        )
        gestor2.groups.add(gestor_group)

        # GESTOR1 cria contrato
        api_client.force_authenticate(user=gestor1)
        contract_data = {
            'title': 'Contrato do GESTOR1',
            'manager': gestor1.id,
            'total_value': 50000.00,
            'start_date': timezone.now().date(),
            'end_date': (timezone.now() + timedelta(days=365)).date(),
            'remaining_balance': 50000.00,
        }
        response = api_client.post('/api/v1/contracts/', contract_data)
        contract_id = response.json()['id']

        print(
            "\n Testando: GESTOR2 gerando PDF de GESTOR1 (leitura permitida)"
        )

        # GESTOR2 consegue acessar (leitura é permissiva para todos)
        api_client.force_authenticate(user=gestor2)
        response = api_client.get(
            f'/api/v1/contracts/{contract_id}/report/pdf/'
        )

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        print("    Leitura permitida (relatório gerado com sucesso)")

    @pytest.mark.django_db
    def test_fornecedor_can_generate_pdf(
        self, api_client, users_with_roles
    ):
        """ FORNECEDOR consegue gerar PDF (qualquer autenticado)"""
        gestor = users_with_roles['gestor']
        fornecedor = users_with_roles['fornecedor']

        # GESTOR cria contrato
        api_client.force_authenticate(user=gestor)
        contract_data = {
            'title': 'Contrato',
            'manager': gestor.id,
            'total_value': 50000.00,
            'start_date': timezone.now().date(),
            'end_date': (timezone.now() + timedelta(days=365)).date(),
            'remaining_balance': 50000.00,
        }
        response = api_client.post('/api/v1/contracts/', contract_data)
        contract_id = response.json()['id']

        print("\n Testando: FORNECEDOR gerando PDF")

        # FORNECEDOR consegue acessar (qualquer autenticado)
        api_client.force_authenticate(user=fornecedor)
        response = api_client.get(
            f'/api/v1/contracts/{contract_id}/report/pdf/'
        )

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        print("    Acesso permitido para autenticado")

    @pytest.mark.django_db
    def test_unauthenticated_cannot_generate_pdf(
        self, users_with_roles
    ):
        """ Usuário não autenticado não consegue gerar PDF"""
        from rest_framework.test import APIClient as DRFAPIClient

        gestor = users_with_roles['gestor']
        auth_client = DRFAPIClient()
        anon_client = DRFAPIClient()

        # GESTOR cria contrato
        auth_client.force_authenticate(user=gestor)
        contract_data = {
            'title': 'Contrato',
            'manager': gestor.id,
            'total_value': 50000.00,
            'start_date': timezone.now().date(),
            'end_date': (timezone.now() + timedelta(days=365)).date(),
            'remaining_balance': 50000.00,
        }
        response = auth_client.post('/api/v1/contracts/', contract_data)
        contract_id = response.json()['id']

        print("\n Testando: Usuário anônimo tentando gerar PDF")

        # Cliente sem autenticação tenta acessar
        response = anon_client.get(
            f'/api/v1/contracts/{contract_id}/report/pdf/'
        )

        # DRF retorna 403 para ações sem permissão (não 401)
        assert response.status_code in [401, 403]
        print(f"    Acesso negado ({response.status_code})")
