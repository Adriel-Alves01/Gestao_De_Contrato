from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.contrib.auth.models import User
from django.http import FileResponse

from .models import Contract, Measurement, Payment, AuditLog
from .serializers import (
    ContractSerializer,
    MeasurementSerializer,
    PaymentSerializer,
    UserSerializer,
    AuditLogSerializer,
)
from .services import (
    ContractService,
    MeasurementService,
    PaymentService,
)
from .throttles import (
    StandardUserThrottle,
    WriteOperationThrottle,
    BurstUserThrottle,
    AuditLogThrottle,
)
from .report_generator import ContractReportGenerator
from .notifications import (
    notify_contract_created,
    notify_contract_closed,
    notify_measurement_created,
    notify_measurement_approved,
    notify_payment_paid,
)


def error_response(detail, status_code):
    return Response(
        {"error": {"detail": detail}},
        status=status_code,
    )


class MeasurementPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsMeasurementAllowed(BasePermission):
    """Permission para criar/editar medições.

    Regras:
    - ADMIN/SUPER: podem criar medições em qualquer contrato
    - FORNECEDOR: podem criar medições em qualquer contrato
    - GESTOR: podem criar/editar medições (validação no serializer)
    - Outros: negados
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Safe methods - qualquer um pode ver
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        # Write methods
        if user.is_superuser:
            return True

        groups = {g.name for g in user.groups.all()}
        # ADMIN, GESTOR e FORNECEDOR podem criar medições
        if "ADMIN" in groups or "GESTOR" in groups or "FORNECEDOR" in groups:
            return True

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        if user.is_superuser:
            return True

        groups = {g.name for g in user.groups.all()}
        if "ADMIN" in groups:
            return True

        # FORNECEDOR só pode ver/criar, não editar
        if "FORNECEDOR" in groups:
            return request.method in ("GET", "HEAD", "OPTIONS")

        # GESTOR pode editar se é o manager do contrato
        if "GESTOR" in groups and hasattr(obj, "contract"):
            return obj.contract.manager_id == user.id

        return False


class IsAdminOrManager(BasePermission):
    """Permission que permite acesso total a ADMINs e acesso restrito a GESTOR.

    Regras básicas:
    - superusers e usuários no grupo 'ADMIN' têm acesso completo.
    - usuários no grupo 'GESTOR' podem criar contratos e modificar apenas
      contratos cujo `manager` seja eles mesmos.
    - outros usuários são negados para ações de escrita.
    """

    def has_permission(self, request, view):
        # Permite leitura para qualquer usuário autenticado; escrita apenas
        # para ADMIN ou GESTOR.
        user = request.user
        # se não tiver usuário ou não estiver autenticado, nega acesso
        if not user or not user.is_authenticated:
            return False

        # Safe methods; escrita apenas para ADMIN/GESTOR
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        if user.is_superuser:
            return True

        groups = {g.name for g in user.groups.all()}
        if "ADMIN" in groups:
            return True

        if "GESTOR" in groups:
            return True

        return False

    def has_object_permission(self, request, view, obj):
        # Para operações em objeto existente, ADMIN ou o manager do contrato
        # podem modificar; leitura permitida para qualquer autenticado.
        user = request.user
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        if user.is_superuser:
            return True

        groups = {g.name for g in user.groups.all()}
        if "ADMIN" in groups:
            return True

        if "GESTOR" in groups:
            # Se o objeto é um Contract, verifica se é o manager
            if hasattr(obj, "manager"):
                return obj.manager_id == user.id
            # Se o objeto é um Measurement, verifica se é manager do contrato
            elif hasattr(obj, "contract"):
                return obj.contract.manager_id == user.id

        return False


class ContractViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciamento completo de contratos.

    ## Operações Disponíveis:

    - **list**: Lista todos os contratos não deletados
    - **retrieve**: Obtém detalhes de um contrato específico
    - **create**: Cria novo contrato (requer GESTOR, ADMIN ou SUPER)
    - **update**: Atualiza contrato existente (apenas manager ou ADMIN)
    - **partial_update**: Atualização parcial (apenas manager ou ADMIN)
    - **destroy**: Soft delete (marca como deletado sem remover do banco)
    - **close**: Ação customizada para encerrar contrato

    ## Permissões:

    - Leitura (GET): Qualquer usuário autenticado
    - Escrita (POST/PUT/PATCH/DELETE): GESTOR (próprio contrato),
      ADMIN ou SUPER

    ## Regras de Negócio:

    - Contratos deletados não aparecem em listagens (soft delete)
    - Cada mudança de status é registrada em ContractStatusHistory
    - GESTOR só pode gerenciar contratos onde é o manager
    - Fechamento de contrato registra auditória completa
    """

    queryset = Contract.objects.filter(is_deleted=False).order_by(
        "-created_at"
    )
    serializer_class = ContractSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['status', 'manager']
    search_fields = ['title', 'description']
    # Rate limiting: operações de leitura 1000/hora, escrita 200/hora
    throttle_classes = [StandardUserThrottle, WriteOperationThrottle]

    def get_throttles(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [StandardUserThrottle()]
        return [WriteOperationThrottle()]

    def get_permissions(self):
        # Combina permissões: exige autenticação sempre e aplica checks
        # de RBAC via `IsAdminOrManager` para métodos de escrita.
        perms = [IsAuthenticated()]
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            perms.append(IsAdminOrManager())
        return perms

    def perform_create(self, serializer):
        # Se o cliente não informar `manager`, atribuímos o usuário que criou.
        data = serializer.validated_data
        manager = data.get("manager")
        if manager is None:
            instance = serializer.save(manager=self.request.user)
        else:
            instance = serializer.save()

        # Registra no AuditLog manualmente
        AuditLog.objects.create(
            user=self.request.user,
            action=AuditLog.Action.CREATE,
            model_name='Contract',
            object_id=instance.id,
            object_display=str(instance),
            changes={},
        )

        notify_contract_created(instance, self.request.user)

    @action(detail=True, methods=("post",), url_path="close")
    def close(self, request, pk=None):
        """
        Fecha um contrato (status → CLOSED).

        ## Descrição:
        Encerra um contrato ativo, alterando seu status para CLOSED e
        registrando a mudança no histórico com auditória completa
        (quem fechou e quando).

        ## Permissões:
        - GESTOR que é o manager do contrato
        - ADMIN ou SUPER (qualquer contrato)

        ## Resposta de Sucesso:
        ```json
        {
            "detail": "Contract closed.",
            "status": "CLOSED"
        }
        ```

        ## Possíveis Erros:
        - **400**: Contrato já está fechado
        - **403**: Usuário não tem permissão
        - **404**: Contrato não encontrado
        """
        contract = self.get_object()

        # Checagem de permissão a nível de objeto
        perm = IsAdminOrManager()
        if not perm.has_object_permission(request, self, contract):
            return error_response(
                "Permission denied.",
                status.HTTP_403_FORBIDDEN,
            )

        try:
            contract = ContractService.close_contract(contract, request.user)
            notify_contract_closed(contract, request.user)
            return Response(
                {"detail": "Contract closed.", "status": contract.status},
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=("get",),
        url_path="report/pdf",
        permission_classes=[IsAuthenticated]
    )
    def report_pdf(self, request, pk=None):
        """
        Gera relatório em PDF do contrato.

        ## Descrição:
        Gera um relatório profissional em PDF contendo:
        - Dados gerais do contrato
        - Todas as medições associadas
        - Todos os pagamentos realizados
        - Status financeiro

        ## Permissões:
        - Qualquer usuário autenticado pode gerar PDF

        ## Resposta de Sucesso:
        - Content-Type: application/pdf
        - Arquivo para download
        - Nome: contrato_{id}_{data}.pdf

        ## Possíveis Erros:
        - **404**: Contrato não encontrado
        - **401**: Não autenticado
        """
        contract = self.get_object()

        try:
            # Gera PDF
            generator = ContractReportGenerator()
            pdf_buffer = generator.generate_contract_report(contract)

            # Prepara resposta com arquivo
            filename = (
                f"contrato_{contract.id}_"
                f"{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )

            return FileResponse(
                pdf_buffer,
                as_attachment=True,
                filename=filename,
                content_type='application/pdf'
            )
        except Exception as e:
            return error_response(
                f"Erro ao gerar PDF: {str(e)}",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        """
        Remove logicamente um contrato (soft delete).

        ## Descrição:
        Em vez de deletar fisicamente do banco, marca o contrato como
        deletado (is_deleted=True) preservando todos os dados para
        auditória e possível recuperação futura.

        ## Auditória:
        Registra quem deletou e quando (deleted_by, deleted_at).

        ## Permissões:
        - GESTOR que é o manager do contrato
        - ADMIN ou SUPER (qualquer contrato)

        ## Nota:
        Contratos deletados não aparecem em listagens, mas permanecem
        no banco de dados para compliance e rastreabilidade.
        """
        contract = self.get_object()
        contract.is_deleted = True
        contract.deleted_at = timezone.now()
        contract.deleted_by = request.user
        contract.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class MeasurementViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciamento de medições de contratos.

    ## Operações Disponíveis:

    - **list**: Lista todas as medições
    - **retrieve**: Obtém detalhes de uma medição específica
    - **create**: Cria nova medição (FORNECEDOR, GESTOR ou ADMIN)
    - **update**: Atualiza medição (apenas manager do contrato ou ADMIN)
    - **approve**: Ação para aprovar medição (GESTOR-dono do contrato)
    - **reject**: Ação para rejeitar medição (GESTOR-dono do contrato)

    ## Permissões:

    - Leitura (GET): Qualquer usuário autenticado
        - Criação: ADMIN, FORNECEDOR (qualquer contrato),
            GESTOR (apenas seus contratos)
    - Aprovação/Rejeição: Apenas GESTOR-dono do contrato

    ## Regras de Negócio:

    - Não pode criar medição em contrato CLOSED
    - GESTOR só pode criar medição em contratos que gerencia
    - Status muda apenas via ações approve/reject
    - Medição já aprovada não pode ser rejeitada (e vice-versa)
    - Apenas medições APPROVED podem receber pagamentos
    """

    queryset = Measurement.objects.all().order_by("-created_at")
    serializer_class = MeasurementSerializer
    permission_classes = (IsAuthenticated, IsMeasurementAllowed)
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['contract', 'status', 'created_by']
    search_fields = ['description']
    pagination_class = MeasurementPagination
    # Rate limiting dinâmico: leitura relaxada, escrita mais restrita
    throttle_classes = [StandardUserThrottle, BurstUserThrottle]

    def get_throttles(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [StandardUserThrottle()]
        return [BurstUserThrottle()]

    def get_permissions(self):
        perms = [IsAuthenticated()]
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            perms.append(IsMeasurementAllowed())
        return perms

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_create(self, serializer):
        instance = serializer.save()
        notify_measurement_created(instance, self.request.user)

    def destroy(self, request, *args, **kwargs):
        """Exclui medição apenas quando status está PENDING."""
        measurement = self.get_object()

        if measurement.status in (
            Measurement.Status.APPROVED,
            Measurement.Status.REJECTED,
        ):
            return error_response(
                "Cannot delete an approved or rejected measurement.",
                status.HTTP_400_BAD_REQUEST,
            )

        self.perform_destroy(measurement)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=("post",),
        url_path="approve",
        permission_classes=[IsAuthenticated]
    )
    def approve(self, request, pk=None):
        """
        Aprova uma medição (status → APPROVED).

        ## Descrição:
        Marca uma medição como aprovada, alterando seu status para
        APPROVED e registrando a data de aprovação. Apenas medições
        aprovadas podem receber pagamentos.

        ## Permissões:
        - GESTOR que é o manager do contrato relacionado
        - ADMIN ou SUPER (qualquer medição)

        ## Resposta de Sucesso:
        ```json
        {
            "detail": "Measurement approved.",
            "id": 1,
            "status": "APPROVED"
        }
        ```

        ## Possíveis Erros:
        - **400**: Medição já está aprovada ou foi rejeitada
        - **403**: Usuário não é manager do contrato
        - **404**: Medição não encontrada
        """
        measurement = self.get_object()
        contract = measurement.contract

        perm = IsAdminOrManager()
        if not perm.has_object_permission(request, self, contract):
            return error_response(
                "Permission denied.",
                status.HTTP_403_FORBIDDEN,
            )

        try:
            measurement = MeasurementService.approve_measurement(
                measurement, request.user
            )
            notify_measurement_approved(measurement, request.user)
            return Response(
                {
                    "detail": "Measurement approved.",
                    "id": measurement.id,
                    "status": measurement.status,
                },
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=("post",),
        url_path="reject",
        permission_classes=[IsAuthenticated]
    )
    def reject(self, request, pk=None):
        """
        Rejeita uma medição (status → REJECTED).

        ## Descrição:
        Marca uma medição como rejeitada, alterando seu status para
        REJECTED e registrando a data de rejeição. Medições rejeitadas
        não podem receber pagamentos.

        ## Permissões:
        - GESTOR que é o manager do contrato relacionado
        - ADMIN ou SUPER (qualquer medição)

        ## Resposta de Sucesso:
        ```json
        {
            "detail": "Measurement rejected.",
            "id": 1,
            "status": "REJECTED"
        }
        ```

        ## Possíveis Erros:
        - **400**: Medição já foi rejeitada ou está aprovada
        - **403**: Usuário não é manager do contrato
        - **404**: Medição não encontrada
        """
        measurement = self.get_object()
        contract = measurement.contract

        perm = IsAdminOrManager()
        if not perm.has_object_permission(request, self, contract):
            return error_response(
                "Permission denied.",
                status.HTTP_403_FORBIDDEN,
            )

        try:
            measurement = MeasurementService.reject_measurement(
                measurement, request.user
            )
            return Response(
                {
                    "detail": "Measurement rejected.",
                    "id": measurement.id,
                    "status": measurement.status,
                },
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=("post",),
        url_path="reopen",
        permission_classes=[IsAuthenticated]
    )
    def reopen(self, request, pk=None):
        """
        Reabre uma medição rejeitada (apenas ADMIN).

        ## Descrição:
        Reverte uma rejeição, convertendo status de REJECTED → PENDING
        para permitir que a medição seja aprovada novamente.

        **IMPORTANTE**: Apenas ADMIN ou SUPER podem usar esta ação.
        Registra a reversão no AuditLog completo.

        ## Permissões:
        - ADMIN ou SUPER únicamente

        ## Resposta de Sucesso:
        ```json
        {
            "detail": "Measurement reopened.",
            "id": 1,
            "status": "PENDING"
        }
        ```

        ## Possíveis Erros:
        - **400**: Medição não está rejeitada
        - **403**: Usuário não é ADMIN
        - **404**: Medição não encontrada
        """
        measurement = self.get_object()

        # Apenas ADMIN/SUPER podem reabrir medições
        user = request.user
        if not user.is_superuser:
            groups = {g.name for g in user.groups.all()}
            if "ADMIN" not in groups:
                return error_response(
                    "Only admins can reopen measurements.",
                    status.HTTP_403_FORBIDDEN,
                )

        try:
            measurement = MeasurementService.reopen_measurement(
                measurement, request.user
            )
            return Response(
                {
                    "detail": "Measurement reopened.",
                    "id": measurement.id,
                    "status": measurement.status,
                },
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciamento de pagamentos.

    ## Operações Disponíveis:

    - **list**: Lista todos os pagamentos
    - **retrieve**: Obtém detalhes de um pagamento específico
    - **create**: Cria novo pagamento (FINANCEIRO ou ADMIN)
    - **mark_as_paid**: Marca pagamento como pago (FINANCEIRO ou ADMIN)
    - **mark_as_failed**: Marca pagamento como falho (FINANCEIRO ou ADMIN)

    ## Permissões:

    - Leitura (GET): Qualquer usuário autenticado
    - Escrita: Apenas FINANCEIRO, ADMIN ou SUPER

    ## Regras de Negócio:

    - Pagamento só pode ser criado para medição APPROVED
    - Valor do pagamento não pode exceder valor da medição
    - Apenas um pagamento por medição
    - Marcação como PAID decrementa saldo do contrato (transação atômica)
    - Pagamento PAID não pode ser marcado como FAILED
    """

    queryset = Payment.objects.all().order_by("-created_at")
    serializer_class = PaymentSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['contract', 'status', 'created_by']
    search_fields = ['measurement__description']
    pagination_class = None  # Usa paginação padrão do settings
    # Rate limiting dinâmico: leitura relaxada, escrita mais restrita
    throttle_classes = [StandardUserThrottle, BurstUserThrottle]

    def get_throttles(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [StandardUserThrottle()]
        return [BurstUserThrottle()]

    def get_permissions(self):
        perms = [IsAuthenticated()]
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            # Para create/update/delete: apenas FINANCEIRO ou ADMIN
            perms.append(IsFinancialOrAdmin())
        return perms

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def create(self, request, *args, **kwargs):
        """Criação manual de pagamento é bloqueada por regra de negócio."""
        return error_response(
            "Payments are created automatically from approved measurements.",
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(
        detail=True,
        methods=("post",),
        url_path="mark-as-paid",
        permission_classes=[IsAuthenticated]
    )
    def mark_as_paid(self, request, pk=None):
        """
        Marca um pagamento como pago (status → PAID).

        ## Descrição:
        Marca um pagamento como PAID, registra a data de pagamento e
        **decrementa automaticamente o saldo do contrato** em uma
        transação atômica (garante consistência financeira).

        ## Permissões:
        - FINANCEIRO
        - ADMIN ou SUPER

        ## Operação Atômica:
        ```
        payment.status = PAID
        payment.paid_at = now()
        contract.remaining_balance -= payment.amount
        ```
        Se qualquer operação falhar, tudo é revertido (rollback).

        ## Resposta de Sucesso:
        ```json
        {
            "detail": "Payment marked as paid.",
            "id": 1,
            "status": "PAID"
        }
        ```

        ## Possíveis Erros:
        - **400**: Pagamento já está marcado como pago
        - **403**: Usuário não é FINANCEIRO ou ADMIN
        - **404**: Pagamento não encontrado
        """
        payment = self.get_object()

        perm = IsFinancialOrAdmin()
        if not perm.has_permission(request, self):
            return error_response(
                "Permission denied.",
                status.HTTP_403_FORBIDDEN,
            )

        try:
            payment = PaymentService.mark_as_paid(payment, request.user)
            contract = payment.contract
            notify_payment_paid(payment, request.user)
            return Response(
                {
                    "detail": "Payment marked as paid.",
                    "id": payment.id,
                    "status": payment.status,
                    "contract_remaining_balance": str(
                        contract.remaining_balance
                    ),
                },
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=("post",),
        url_path="mark-as-failed",
        permission_classes=[IsAuthenticated]
    )
    def mark_as_failed(self, request, pk=None):
        """
        Marca um pagamento como falhado (status → FAILED).

        ## Descrição:
        Marca um pagamento como FAILED quando o processamento falha
        (ex: cartão recusado, saldo insuficiente, erro no gateway).
        Não altera o saldo do contrato.

        ## Permissões:
        - FINANCEIRO
        - ADMIN ou SUPER

        ## Restrições:
        - Pagamento já PAID não pode ser marcado como FAILED
        - Pagamento já FAILED não pode ser marcado novamente

        ## Resposta de Sucesso:
        ```json
        {
            "detail": "Payment marked as failed.",
            "id": 1,
            "status": "FAILED"
        }
        ```

        ## Possíveis Erros:
        - **400**: Pagamento já está PAID ou FAILED
        - **403**: Usuário não é FINANCEIRO ou ADMIN
        - **404**: Pagamento não encontrado
        """
        payment = self.get_object()

        perm = IsFinancialOrAdmin()
        if not perm.has_permission(request, self):
            return error_response(
                "Permission denied.",
                status.HTTP_403_FORBIDDEN,
            )

        try:
            payment = PaymentService.mark_as_failed(payment, request.user)
            return Response(
                {
                    "detail": "Payment marked as failed.",
                    "id": payment.id,
                    "status": payment.status,
                },
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)


class IsFinancialOrAdmin(BasePermission):
    """Permission que permite acesso apenas para FINANCEIRO e ADMIN."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        groups = {g.name for g in user.groups.all()}
        if "ADMIN" in groups:
            return True

        if "FINANCEIRO" in groups:
            return True

        return False


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para listar usuários do sistema.

    ## Operações Disponíveis:

    - **list**: Lista todos os usuários (apenas ADMIN)
    - **retrieve**: Obtém detalhes de um usuário específico

    ## Permissões:

    - Apenas usuários autenticados podem visualizar
    - Apenas ADMIN ou SUPER podem listar todos

    ## Casos de Uso:

    - Admin precisando atribuir um GESTOR a um contrato
    - Frontend preenchendo dropdown com usuários disponíveis
    """

    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    # Rate limiting: operações de leitura 500/hora
    throttle_classes = [StandardUserThrottle]

    def get_permissions(self):
        """Apenas ADMIN/SUPER podem listar usuários."""
        if self.request.method == 'GET':
            perms = [IsAuthenticated()]
            # Verifica se é ADMIN ou SUPER
            user = self.request.user
            if not user.is_superuser:
                groups = {g.name for g in user.groups.all()}
                if "ADMIN" not in groups:
                    # Não é ADMIN, retorna 403
                    perms.append(IsFinancialOrAdmin())
            return perms
        return [IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        """Lista todos os usuários (apenas ADMIN/SUPER)."""
        user = request.user
        if not user.is_superuser:
            groups = {g.name for g in user.groups.all()}
            if "ADMIN" not in groups:
                return error_response(
                    "Permission denied. Only ADMIN can list users.",
                    status.HTTP_403_FORBIDDEN,
                )
        return super().list(request, *args, **kwargs)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para visualizar logs de auditoria.

    ## Operações Disponíveis:

    - **list**: Lista todos os logs de auditoria (filtráveis)
    - **retrieve**: Obtém detalhes de um log específico

    ## Permissões:

    - Apenas usuários autenticados podem visualizar
    - Apenas ADMIN ou SUPER têm acesso completo
    - Outros usuários veem apenas seus próprios logs

    ## Campos Importantes:

    - **action**: CREATE, UPDATE, DELETE, APPROVE, REJECT, PAID, FAILED
    - **model_name**: Contract, Measurement, Payment, User
    - **object_id**: ID do objeto afetado
    - **changes**: JSON com campos alterados (before/after)
    - **timestamp**: Quando a ação ocorreu
    - **user**: Quem fez a ação
    - **ip_address**: De onde veio a requisição

    ## Filtros Disponíveis:

    - `action`: Tipo de ação (CREATE, UPDATE, DELETE, etc)
    - `model_name`: Tipo de modelo (Contract, Measurement, etc)
    - `user`: Quem fez a ação (ID do usuário)
    - `object_id`: ID do objeto afetado

    ## Casos de Uso:

    - Admin rastreando mudanças no sistema
    - Compliance: quem fez o quê, quando e por quê
    - Debug: encontrar quando um campo foi alterado
    - Segurança: detectar atividades suspeitas
    """

    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['action', 'model_name', 'user', 'object_id']
    search_fields = ['object_display', 'user__username']
    # Rate limiting: apenas leitura (audit), limite relaxado 500/hora
    throttle_classes = [AuditLogThrottle]

    def get_queryset(self):
        """Controla acesso: ADMINs veem tudo, outros veem só seus logs."""
        user = self.request.user
        queryset = AuditLog.objects.all()

        # ADMIN/SUPER veem tudo
        if user.is_superuser:
            return queryset

        groups = {g.name for g in user.groups.all()}
        if "ADMIN" in groups:
            return queryset

        # Outros usuários veem apenas seus próprios logs
        return queryset.filter(user=user)
