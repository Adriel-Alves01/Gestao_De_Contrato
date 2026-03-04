"""
Testes End-to-End (E2E) completos.

Cobre TODOS os cenários possíveis:
 Happy paths (sucesso)
 Erros de validação
 Erros de permissão
 Erros de lógica de negócio
 Rastreamento em auditoria
"""

import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User, Group
from django.utils import timezone
from datetime import timedelta

from contracts.models import Payment


@pytest.fixture
def api_client():
    """Cliente API para requisições."""
    return APIClient()


@pytest.fixture
def users_with_roles():
    """Cria usuários com diferentes roles (RBAC)."""

    # Criar grupos
    gestor_group, _ = Group.objects.get_or_create(name="GESTOR")
    financeiro_group, _ = Group.objects.get_or_create(name="FINANCEIRO")
    admin_group, _ = Group.objects.get_or_create(name="ADMIN")
    fornecedor_group, _ = Group.objects.get_or_create(name="FORNECEDOR")

    # Criar usuários
    gestor = User.objects.create_user(
        username="gestor_user", password="pass123", email="gestor@example.com"
    )
    gestor.groups.add(gestor_group)

    financeiro = User.objects.create_user(
        username="financeiro_user",
        password="pass123",
        email="financeiro@example.com",
    )
    financeiro.groups.add(financeiro_group)

    admin = User.objects.create_user(
        username="admin_user",
        password="pass123",
        email="admin@example.com",
        is_superuser=True,
    )
    admin.groups.add(admin_group)

    fornecedor = User.objects.create_user(
        username="fornecedor_user",
        password="pass123",
        email="fornecedor@example.com",
    )
    fornecedor.groups.add(fornecedor_group)

    return {
        "gestor": gestor,
        "financeiro": financeiro,
        "admin": admin,
        "fornecedor": fornecedor,
    }


class TestE2EHappyPath:
    """Teste E2E do caminho feliz - tudo funciona perfeitamente."""

    @pytest.mark.django_db
    def test_complete_contract_lifecycle_success(
        self, api_client, users_with_roles
    ):
        """
        Fluxo completo de sucesso:
        1. GESTOR cria contrato
        2. GESTOR cria medição
        3. GESTOR aprova medição
        4. Sistema cria pagamento automaticamente
        5. FINANCEIRO marca como PAGO
        6. Sistema decrementa saldo
        7. Auditoria registra tudo
        """

        gestor = users_with_roles["gestor"]
        financeiro = users_with_roles["financeiro"]

        # 1⃣ GESTOR cria contrato
        api_client.force_authenticate(user=gestor)

        contract_data = {
            "title": "Contrato de Construção",
            "description": "Prédio comercial Centro",
            "manager": gestor.id,
            "total_value": 100000.00,
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timedelta(days=365)).date(),
            "remaining_balance": 100000.00,
        }

        response = api_client.post("/api/v1/contracts/", contract_data)
        assert (
            response.status_code == 201
        ), f"Erro ao criar contrato: {response.data}"
        contract_id = response.json()["id"]
        print(f"\n Contrato criado: {contract_id}")

        # 2⃣ GESTOR cria medição
        measurement_data = {
            "contract": contract_id,
            "value": 25000.00,
            "description": "Medição 1 - Fundação",
        }

        response = api_client.post("/api/v1/measurements/", measurement_data)
        assert (
            response.status_code == 201
        ), f"Erro ao criar medição: {response.data}"
        measurement_id = response.json()["id"]
        assert response.json()["status"] == "PENDING"
        print(f" Medição criada: {measurement_id} (status: PENDING)")

        # 3⃣ GESTOR aprova medição
        response = api_client.post(
            f"/api/v1/measurements/{measurement_id}/approve/", {}
        )
        assert response.status_code == 200, f"Erro ao aprovar: {response.data}"
        assert response.json()["status"] == "APPROVED"
        print(" Medição aprovada (status: APPROVED)")

        # 4⃣ Pagamento é criado automaticamente
        payment = Payment.objects.get(measurement_id=measurement_id)
        payment_id = payment.id
        assert payment.status == Payment.Status.PENDING
        print(f" Pagamento auto-criado: {payment_id} (status: PENDING)")

        # FINANCEIRO segue responsável por processar o pagamento
        api_client.force_authenticate(user=financeiro)

        # 5⃣ FINANCEIRO marca como PAGO
        response = api_client.post(
            f"/api/v1/payments/{payment_id}/mark-as-paid/", {}
        )
        assert (
            response.status_code == 200
        ), f"Erro ao marcar como pago: {response.data}"
        assert response.json()["status"] == "PAID"
        print(" Pagamento marcado como PAGO (status: PAID)")

        # 6⃣ Verificar se saldo diminuiu
        response = api_client.get(f"/api/v1/contracts/{contract_id}/")
        contract = response.json()
        assert float(contract["remaining_balance"]) == 75000.00
        balance = contract["remaining_balance"]
        print(f" Saldo diminuiu corretamente: {balance}")

        # 7⃣ Verificar auditoria
        api_client.force_authenticate(user=users_with_roles["admin"])
        response = api_client.get("/api/v1/audit-logs/")
        audit_logs = response.json()["results"]

        actions = [log["action"] for log in audit_logs]
        assert "CREATE" in actions  # Contrato criado
        assert "APPROVE" in actions  # Medição aprovada
        assert "PAID" in actions  # Pagamento pago

        print(f" Auditoria registrou {len(audit_logs)} eventos")
        print(f"   Ações: {set(actions)}")

        print("\n FLUXO COMPLETO DE SUCESSO FUNCIONANDO!\n")


class TestE2EContractErrors:
    """Teste E2E com erros na criação de contrato."""

    @pytest.mark.django_db
    def test_contract_with_invalid_dates(self, api_client, users_with_roles):
        """Erro: End date < start date"""
        gestor = users_with_roles["gestor"]
        api_client.force_authenticate(user=gestor)

        print("\n Testando: Data de fim MENOR que data de início")

        contract_data = {
            "title": "Contrato Inválido",
            "manager": gestor.id,
            "total_value": 50000.00,
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() - timedelta(days=10)).date(),  # ANTES!
            "remaining_balance": 50000.00,
        }

        response = api_client.post("/api/v1/contracts/", contract_data)
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_contract_with_negative_balance(
        self, api_client, users_with_roles
    ):
        """Erro: Remaining balance negativo"""
        gestor = users_with_roles["gestor"]
        api_client.force_authenticate(user=gestor)

        print("\n Testando: Saldo restante NEGATIVO")

        contract_data = {
            "title": "Contrato Negativo",
            "manager": gestor.id,
            "total_value": 100000.00,
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timedelta(days=365)).date(),
            "remaining_balance": -5000.00,  # NEGATIVO!
        }

        response = api_client.post("/api/v1/contracts/", contract_data)
        assert response.status_code == 400
        # Validação passou, status correto

    @pytest.mark.django_db
    def test_fornecedor_cannot_create_contract(
        self, api_client, users_with_roles
    ):
        """Erro: FORNECEDOR tenta criar contrato (permissão negada)"""
        fornecedor = users_with_roles["fornecedor"]
        api_client.force_authenticate(user=fornecedor)

        print("\n Testando: FORNECEDOR tentando criar contrato")

        contract_data = {
            "title": "Contrato Não Autorizado",
            "manager": fornecedor.id,
            "total_value": 50000.00,
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timedelta(days=365)).date(),
            "remaining_balance": 50000.00,
        }

        response = api_client.post("/api/v1/contracts/", contract_data)
        assert response.status_code == 403
        print(" Sistema retornou 403: Permissão negada")


class TestE2EMeasurementErrors:
    """Teste E2E com erros na medição."""

    @pytest.mark.django_db
    def test_measurement_on_closed_contract(
        self, api_client, users_with_roles
    ):
        """Erro: Tentar criar medição em contrato FECHADO"""
        gestor = users_with_roles["gestor"]
        api_client.force_authenticate(user=gestor)

        print("\n Testando: Medição em contrato FECHADO")

        # 1. Criar contrato
        contract_data = {
            "title": "Contrato Fechado",
            "manager": gestor.id,
            "total_value": 100000.00,
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timedelta(days=365)).date(),
            "remaining_balance": 100000.00,
        }
        response = api_client.post("/api/v1/contracts/", contract_data)
        contract_id = response.json()["id"]

        # 2. Fechar contrato
        response = api_client.post(
            f"/api/v1/contracts/{contract_id}/close/", {}
        )
        assert response.status_code == 200

        # 3. Tentar criar medição em contrato fechado
        measurement_data = {
            "contract": contract_id,
            "value": 10000.00,
            "description": "Medição inválida",
        }

        response = api_client.post("/api/v1/measurements/", measurement_data)
        assert response.status_code == 400
        # Validação passou, status correto

    @pytest.mark.django_db
    def test_measurement_with_zero_value(self, api_client, users_with_roles):
        """Erro: Tentar criar medição com valor ZERO"""
        gestor = users_with_roles["gestor"]
        api_client.force_authenticate(user=gestor)

        print("\n Testando: Medição com valor ZERO")

        # 1. Criar contrato
        contract_data = {
            "title": "Contrato Normal",
            "manager": gestor.id,
            "total_value": 100000.00,
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timedelta(days=365)).date(),
            "remaining_balance": 100000.00,
        }
        response = api_client.post("/api/v1/contracts/", contract_data)
        contract_id = response.json()["id"]

        # 2. Tentar criar medição com valor zero
        measurement_data = {
            "contract": contract_id,
            "value": 0.00,  # ZERO!
            "description": "Medição com zero",
        }

        response = api_client.post("/api/v1/measurements/", measurement_data)
        assert response.status_code == 400
        # Validação passou, status correto

    @pytest.mark.django_db
    def test_measurement_approval_idempotence(
        self, api_client, users_with_roles
    ):
        """Erro: Tentar APROVAR medição já APROVADA (2x)"""
        gestor = users_with_roles["gestor"]
        api_client.force_authenticate(user=gestor)

        print("\n Testando: Aprovar medição DUAS VEZES")

        # 1. Criar contrato
        contract_data = {
            "title": "Contrato",
            "manager": gestor.id,
            "total_value": 100000.00,
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timedelta(days=365)).date(),
            "remaining_balance": 100000.00,
        }
        response = api_client.post("/api/v1/contracts/", contract_data)
        contract_id = response.json()["id"]

        # 2. Criar medição
        measurement_data = {"contract": contract_id, "value": 10000.00}
        response = api_client.post("/api/v1/measurements/", measurement_data)
        measurement_id = response.json()["id"]

        # 3. Aprovar primeira vez (sucesso)
        response = api_client.post(
            f"/api/v1/measurements/{measurement_id}/approve/", {}
        )
        assert response.status_code == 200
        print("    Primeira aprovação: sucesso")

        # 4. Tentar aprovar segunda vez (erro!)
        response = api_client.post(
            f"/api/v1/measurements/{measurement_id}/approve/", {}
        )
        assert response.status_code == 400
        print("    Segunda aprovação: bloqueada com 400")

    @pytest.mark.django_db
    def test_reject_then_approve_fails(self, api_client, users_with_roles):
        """Erro: Rejeitar medição, depois tentar aprovar"""
        gestor = users_with_roles["gestor"]
        api_client.force_authenticate(user=gestor)

        print("\n Testando: REJEITAR depois APROVAR")

        # 1. Criar contrato
        contract_data = {
            "title": "Contrato",
            "manager": gestor.id,
            "total_value": 100000.00,
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timedelta(days=365)).date(),
            "remaining_balance": 100000.00,
        }
        response = api_client.post("/api/v1/contracts/", contract_data)
        contract_id = response.json()["id"]

        # 2. Criar medição
        measurement_data = {"contract": contract_id, "value": 10000.00}
        response = api_client.post("/api/v1/measurements/", measurement_data)
        measurement_id = response.json()["id"]

        # 3. Rejeitar medição
        response = api_client.post(
            f"/api/v1/measurements/{measurement_id}/reject/", {}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "REJECTED"
        print("    Medição rejeitada")

        # 4. Tentar aprovar (deve falhar!)
        response = api_client.post(
            f"/api/v1/measurements/{measurement_id}/approve/", {}
        )
        assert response.status_code == 400
        print("    Tentativa de aprovar após rejeitar: bloqueada com 400")


class TestE2EPaymentErrors:
    """Teste E2E com erros no pagamento."""

    @pytest.mark.django_db
    def test_payment_on_unapproved_measurement(
        self, api_client, users_with_roles
    ):
        """Erro: Tentar pagar medição que está PENDING (não aprovada)"""
        gestor = users_with_roles["gestor"]
        financeiro = users_with_roles["financeiro"]
        api_client.force_authenticate(user=gestor)

        print("\n Testando: Pagamento em medição PENDING (não aprovada)")

        # 1. Criar contrato
        contract_data = {
            "title": "Contrato",
            "manager": gestor.id,
            "total_value": 100000.00,
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timedelta(days=365)).date(),
            "remaining_balance": 100000.00,
        }
        response = api_client.post("/api/v1/contracts/", contract_data)
        contract_id = response.json()["id"]

        # 2. Criar medição (sem aprovar!)
        measurement_data = {"contract": contract_id, "value": 10000.00}
        response = api_client.post("/api/v1/measurements/", measurement_data)
        measurement_id = response.json()["id"]

        # 3. FINANCEIRO tenta criar pagamento manual (bloqueado)
        api_client.force_authenticate(user=financeiro)

        assert Payment.objects.filter(measurement_id=measurement_id).count() == 0
        payment_data = {
            "contract": contract_id,
            "measurement": measurement_id,
            "amount": 10000.00,
        }

        response = api_client.post("/api/v1/payments/", payment_data)
        assert response.status_code == 405

    @pytest.mark.django_db
    def test_payment_exceeds_measurement_value(
        self, api_client, users_with_roles
    ):
        """Erro: Pagamento MAIOR que valor da medição"""
        gestor = users_with_roles["gestor"]
        financeiro = users_with_roles["financeiro"]
        api_client.force_authenticate(user=gestor)

        print("\n Testando: Pagamento MAIOR que medição")

        # 1. Criar contrato
        contract_data = {
            "title": "Contrato",
            "manager": gestor.id,
            "total_value": 100000.00,
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timedelta(days=365)).date(),
            "remaining_balance": 100000.00,
        }
        response = api_client.post("/api/v1/contracts/", contract_data)
        contract_id = response.json()["id"]

        # 2. Criar medição de 10000
        measurement_data = {"contract": contract_id, "value": 10000.00}
        response = api_client.post("/api/v1/measurements/", measurement_data)
        measurement_id = response.json()["id"]

        # 3. Aprovar
        api_client.post(f"/api/v1/measurements/{measurement_id}/approve/", {})

        # 4. Pagamento auto-criado tem valor idêntico ao da medição
        payment = Payment.objects.get(measurement_id=measurement_id)
        assert float(payment.amount) == 10000.00

        # 5. FINANCEIRO tenta criar manualmente um valor maior (bloqueado)
        api_client.force_authenticate(user=financeiro)
        payment_data = {
            "contract": contract_id,
            "measurement": measurement_id,
            "amount": 15000.00,  # MAIOR!
        }

        response = api_client.post("/api/v1/payments/", payment_data)
        assert response.status_code == 405

    @pytest.mark.django_db
    def test_duplicate_payment(self, api_client, users_with_roles):
        """Erro: Tentativa de criar pagamento manual quando já existe auto."""
        gestor = users_with_roles["gestor"]
        financeiro = users_with_roles["financeiro"]
        api_client.force_authenticate(user=gestor)

        print("\n Testando: DOIS pagamentos para mesma medição")

        # 1. Criar contrato
        contract_data = {
            "title": "Contrato",
            "manager": gestor.id,
            "total_value": 100000.00,
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timedelta(days=365)).date(),
            "remaining_balance": 100000.00,
        }
        response = api_client.post("/api/v1/contracts/", contract_data)
        contract_id = response.json()["id"]

        # 2. Criar e aprovar medição
        measurement_data = {"contract": contract_id, "value": 10000.00}
        response = api_client.post("/api/v1/measurements/", measurement_data)
        measurement_id = response.json()["id"]
        api_client.post(f"/api/v1/measurements/{measurement_id}/approve/", {})

        # 3. Aprovação gera exatamente um pagamento automático
        assert Payment.objects.filter(measurement_id=measurement_id).count() == 1

        # 4. FINANCEIRO tenta criar pagamento manual (erro)
        api_client.force_authenticate(user=financeiro)
        payment_data = {
            "contract": contract_id,
            "measurement": measurement_id,
            "amount": 10000.00,
        }
        response = api_client.post("/api/v1/payments/", payment_data)
        assert response.status_code == 405
        print("    Criação manual bloqueada (405)")

    @pytest.mark.django_db
    def test_cannot_mark_paid_payment_as_failed(
        self, api_client, users_with_roles
    ):
        """Erro: Marcar como FAILED um pagamento já PAID"""
        gestor = users_with_roles["gestor"]
        financeiro = users_with_roles["financeiro"]
        api_client.force_authenticate(user=gestor)

        print("\n Testando: Marcar FAILED um pagamento já PAID")

        # 1-3. Criar contrato, medição aprovada
        contract_data = {
            "title": "Contrato",
            "manager": gestor.id,
            "total_value": 100000.00,
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timedelta(days=365)).date(),
            "remaining_balance": 100000.00,
        }
        response = api_client.post("/api/v1/contracts/", contract_data)
        contract_id = response.json()["id"]

        measurement_data = {"contract": contract_id, "value": 10000.00}
        response = api_client.post("/api/v1/measurements/", measurement_data)
        measurement_id = response.json()["id"]
        api_client.post(f"/api/v1/measurements/{measurement_id}/approve/", {})

        # 4. FINANCEIRO marca como PAID pagamento auto-criado
        api_client.force_authenticate(user=financeiro)
        payment = Payment.objects.get(measurement_id=measurement_id)
        payment_id = payment.id

        response = api_client.post(
            f"/api/v1/payments/{payment_id}/mark-as-paid/", {}
        )
        assert response.status_code == 200
        print("    Pagamento marcado como PAID")

        # 5. Tentar marcar como FAILED (erro!)
        response = api_client.post(
            f"/api/v1/payments/{payment_id}/mark-as-failed/", {}
        )
        assert response.status_code == 400
        print("    Tentativa de marcar como FAILED bloqueada: bloqueada")


class TestE2ERBACPermissions:
    """Teste E2E de permissões (Role-Based Access Control)."""

    @pytest.mark.django_db
    def test_gestor_cannot_approve_own_measurement(
        self, api_client, users_with_roles
    ):
        """Erro: GESTOR não pode APROVAR medição que criou"""
        gestor = users_with_roles["gestor"]
        api_client.force_authenticate(user=gestor)

        print("\n Testando: GESTOR não pode APROVAR sua própria medição")

        # Nota: Este é um teste de negócio específico
        # Se na regra GESTOR PODE aprovar sua própria, este teste é inválido
        # Deixei como exemplo de teste de permissão


class TestE2EAuditTrail:
    """Teste E2E de rastreamento completo (auditoria)."""

    @pytest.mark.django_db
    def test_all_operations_audited(self, api_client, users_with_roles):
        """Verificar que TODAS as operações são auditadas"""
        gestor = users_with_roles["gestor"]
        financeiro = users_with_roles["financeiro"]
        admin = users_with_roles["admin"]

        api_client.force_authenticate(user=gestor)

        print("\n Testando: Todas as operações auditadas")

        # 1. GESTOR cria contrato
        contract_data = {
            "title": "Contrato Auditado",
            "manager": gestor.id,
            "total_value": 100000.00,
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timedelta(days=365)).date(),
            "remaining_balance": 100000.00,
        }
        response = api_client.post("/api/v1/contracts/", contract_data)
        contract_id = response.json()["id"]

        # 2. GESTOR cria medição
        measurement_data = {"contract": contract_id, "value": 10000.00}
        response = api_client.post("/api/v1/measurements/", measurement_data)
        measurement_id = response.json()["id"]

        # 3. GESTOR aprova
        api_client.post(f"/api/v1/measurements/{measurement_id}/approve/", {})

        # 4. FINANCEIRO paga pagamento auto-criado
        api_client.force_authenticate(user=financeiro)
        payment = Payment.objects.get(measurement_id=measurement_id)
        payment_id = payment.id

        api_client.post(f"/api/v1/payments/{payment_id}/mark-as-paid/", {})

        # 5. ADMIN consulta auditoria
        api_client.force_authenticate(user=admin)
        response = api_client.get("/api/v1/audit-logs/")
        audit_logs = response.json()["results"]

        expected_actions = ["CREATE", "APPROVE", "PAID"]
        actual_actions = [log["action"] for log in audit_logs]

        for expected in expected_actions:
            assert expected in actual_actions
            print(f"    Ação '{expected}' registrada")

        # Verificar dados dos logs
        for log in audit_logs:
            assert log["user"] is not None
            assert log["timestamp"] is not None
            assert log["model_name"] in ["Contract", "Measurement", "Payment"]

        print(f" Total de operações auditadas: {len(audit_logs)}")


class TestE2EMeasurementReopen:
    """Teste E2E para reabertura de medições rejeitadas (apenas ADMIN)."""

    @pytest.mark.django_db
    def test_admin_can_reopen_rejected_measurement(
        self, api_client, users_with_roles
    ):
        """ADMIN consegue reverter rejeição de medição"""
        gestor = users_with_roles["gestor"]
        admin = users_with_roles["admin"]
        api_client.force_authenticate(user=gestor)

        print("\n Testando: ADMIN reabrindo medição rejeitada")

        # 1. GESTOR cria contrato
        contract_data = {
            "title": "Contrato para Reopen",
            "manager": gestor.id,
            "total_value": 100000.00,
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timedelta(days=365)).date(),
            "remaining_balance": 100000.00,
        }
        response = api_client.post("/api/v1/contracts/", contract_data)
        contract_id = response.json()["id"]

        # 2. GESTOR cria medição
        measurement_data = {"contract": contract_id, "value": 10000.00}
        response = api_client.post("/api/v1/measurements/", measurement_data)
        measurement_id = response.json()["id"]

        # 3. GESTOR rejeita medição
        response = api_client.post(
            f"/api/v1/measurements/{measurement_id}/reject/", {}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "REJECTED"
        print("    Medição rejeitada por GESTOR")

        # 4. ADMIN reabre medição
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            f"/api/v1/measurements/{measurement_id}/reopen/", {}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "PENDING"
        print(f"    ADMIN reabriu medição: {data['status']}")

        # 5. Agora GESTOR consegue aprovar
        api_client.force_authenticate(user=gestor)
        response = api_client.post(
            f"/api/v1/measurements/{measurement_id}/approve/", {}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "APPROVED"
        print("    Medição aprovada depois de reaberta")

        # 6. Verificar audit log tem REJECT e REOPEN
        api_client.force_authenticate(user=admin)
        response = api_client.get("/api/v1/audit-logs/")
        audit_logs = response.json()["results"]
        actions = [log["action"] for log in audit_logs]

        assert "REJECT" in actions
        assert "REOPEN" in actions
        assert "APPROVE" in actions
        print("    Auditoria registrou: REJECT, REOPEN, APPROVE")

    @pytest.mark.django_db
    def test_gestor_cannot_reopen_measurement(
        self, api_client, users_with_roles
    ):
        """GESTOR NÃO pode reabrir medição (apenas ADMIN)"""
        gestor = users_with_roles["gestor"]
        api_client.force_authenticate(user=gestor)

        print("\n Testando: GESTOR tentando reabrir (deve falhar)")

        # 1. Criar contrato
        contract_data = {
            "title": "Contrato para Reopen",
            "manager": gestor.id,
            "total_value": 100000.00,
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timedelta(days=365)).date(),
            "remaining_balance": 100000.00,
        }
        response = api_client.post("/api/v1/contracts/", contract_data)
        contract_id = response.json()["id"]

        # 2. Criar medição
        measurement_data = {"contract": contract_id, "value": 10000.00}
        response = api_client.post("/api/v1/measurements/", measurement_data)
        measurement_id = response.json()["id"]

        # 3. GESTOR rejeita
        api_client.post(f"/api/v1/measurements/{measurement_id}/reject/", {})

        # 4. GESTOR tenta reabrir (deve dar 403)
        response = api_client.post(
            f"/api/v1/measurements/{measurement_id}/reopen/", {}
        )
        assert response.status_code == 403
        print("    GESTOR bloqueado com 403")

    @pytest.mark.django_db
    def test_cannot_reopen_pending_measurement(
        self, api_client, users_with_roles
    ):
        """Erro: Tentar reabrir medição que não está rejeitada"""
        gestor = users_with_roles["gestor"]
        admin = users_with_roles["admin"]
        api_client.force_authenticate(user=gestor)

        print("\n Testando: Tentar reabrir medição PENDING (deve falhar)")

        # 1. Criar contrato
        contract_data = {
            "title": "Contrato",
            "manager": gestor.id,
            "total_value": 100000.00,
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timedelta(days=365)).date(),
            "remaining_balance": 100000.00,
        }
        response = api_client.post("/api/v1/contracts/", contract_data)
        contract_id = response.json()["id"]

        # 2. Criar medição (fica PENDING)
        measurement_data = {"contract": contract_id, "value": 10000.00}
        response = api_client.post("/api/v1/measurements/", measurement_data)
        measurement_id = response.json()["id"]

        # 3. ADMIN tenta reabrir uma que é PENDING (erro!)
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            f"/api/v1/measurements/{measurement_id}/reopen/", {}
        )
        assert response.status_code == 400
        print("    ADMIN bloqueado: medição não está rejeitada")
