from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Contract, Measurement, Payment, AuditLog, Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField(read_only=True)
    file_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Attachment
        fields = ['id', 'file', 'file_name', 'uploaded_by_name', 'created_at']
        read_only_fields = ['id', 'uploaded_by_name', 'created_at']

    def get_uploaded_by_name(self, obj):
        return obj.uploaded_by.get_full_name() or obj.uploaded_by.username

    def get_file_name(self, obj):
        return obj.file.name.split('/')[-1] if obj.file else None


class UserSerializer(serializers.ModelSerializer):
    """Serializer para dados do usuário.

    Mostra informações básicas do usuário sem expor dados sensíveis.
    """

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'username', 'email']


class ContractSerializer(serializers.ModelSerializer):
    remaining_balance = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        allow_null=True
    )
    manager = serializers.SerializerMethodField()
    manager_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
        source='manager'
    )

    class Meta:
        model = Contract
        fields = [
            "id",
            "title",
            "description",
            "total_value",
            "remaining_balance",
            "start_date",
            "end_date",
            "status",
            "numero_contrato",
            "empresa_contratante",
            "empresa_contratada",
            "cnpj_empresa_contratada",
            "cnpj_empresa_contratante",
            "manager",
            "manager_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at", "manager")

    def get_manager(self, obj):
        """Retorna dados completos do manager em leitura."""
        if obj.manager:
            return UserSerializer(obj.manager).data
        return None

    def validate(self, data):
        start = data.get("start_date")
        end = data.get("end_date")
        total = data.get("total_value")
        remaining = data.get("remaining_balance")

        if start and end and end < start:
            raise serializers.ValidationError("end_date must be >= start_date")

        if total is not None and remaining is not None:
            if remaining > total:
                raise serializers.ValidationError(
                    "remaining_balance cannot be greater than total_value"
                )
            if remaining < 0:
                raise serializers.ValidationError(
                    "remaining_balance cannot be negative"
                )

        if (
            total is not None
            and remaining is None
            and self.instance is not None
        ):
            current_remaining = self.instance.remaining_balance
            if current_remaining > total:
                raise serializers.ValidationError(
                    "remaining_balance cannot be greater than total_value"
                )

        return data

    def create(self, validated_data):
        if validated_data.get("remaining_balance") is None:
            validated_data["remaining_balance"] = validated_data["total_value"]

        return super().create(validated_data)

    def update(self, instance, validated_data):
        total_updated = "total_value" in validated_data
        remaining_updated = "remaining_balance" in validated_data

        if total_updated and not remaining_updated:
            old_total = instance.total_value
            old_remaining = instance.remaining_balance

            if old_remaining == old_total:
                validated_data["remaining_balance"] = (
                    validated_data["total_value"]
                )

        return super().update(instance, validated_data)


class MeasurementSerializer(serializers.ModelSerializer):
    """ Serializer para o modelo Measurement.

    Validações:
    - value não pode ser negativo
    - não pode criar medição se contrato está CLOSED
    - status é read-only (muda apenas via ações approve/reject)
    """
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True
    )
    approved_by_name = serializers.SerializerMethodField(read_only=True)
    rejected_by_name = serializers.SerializerMethodField(read_only=True)
    contract_title = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Measurement
        fields = [
            "id",
            "contract",
            "contract_title",
            "created_by",
            "description",
            "value",
            "start_date",
            "end_date",
            "status",
            "approved_at",
            "approved_by_name",
            "rejected_at",
            "rejected_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "approved_at",
            "approved_by_name",
            "rejected_at",
            "rejected_by_name",
            "contract_title",
            "status",
        )

    def get_contract_title(self, obj):
        return obj.contract.title if obj.contract else None

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            full = f"{obj.approved_by.first_name} {
                obj.approved_by.last_name}".strip()

            return full or obj.approved_by.username
        return None

    def get_rejected_by_name(self, obj):
        if obj.rejected_by:
            full = f"{obj.rejected_by.first_name} {
                obj.rejected_by.last_name}".strip()

            return full or obj.rejected_by.username
        return None

    def validate_value(self, value):
        """Garante que o valor da medição é positivo."""
        if value <= 0:
            raise serializers.ValidationError("Value must be greater than 0")
        return value

    def validate_contract(self, contract):
        """Impede criar medição se contrato está CLOSED."""
        if contract.status == Contract.Status.CLOSED:
            raise serializers.ValidationError(
                "Cannot create measurement for a closed contract"
            )
        return contract

    def validate(self, data):
        """Validações cross-field.

        - Se GESTOR: só pode criar medição em contratos que gerencia
        - Se ADMIN/SUPER: pode criar em qualquer contrato
        - Se FORNECEDOR: pode criar em qualquer contrato
        """
        request = self.context.get("request")
        if not request:
            return data

        if self.instance and self.instance.status in (
            Measurement.Status.APPROVED,
            Measurement.Status.REJECTED,
        ):
            raise serializers.ValidationError(
                "Cannot edit a measurement that is approved or rejected"
            )

        user = request.user
        contract = data.get("contract")

        if not contract:
            return data

        # Se for ADMIN ou SUPER, permite tudo
        if user.is_superuser:
            return data

        groups = {g.name for g in user.groups.all()}
        if "ADMIN" in groups:
            return data

        # Se for FORNECEDOR, pode criar em qualquer contrato
        if "FORNECEDOR" in groups:
            return data

        # Se for GESTOR, valida se é manager do contrato
        if "GESTOR" in groups:
            if contract.manager_id != user.id:
                raise serializers.ValidationError(
                    "You can only create measurements for contracts "
                    "where you are the manager"
                )

        # Valida que data de fim não é anterior à data de início
        start = data.get("start_date")
        end = data.get("end_date")
        if start and end and end < start:
            raise serializers.ValidationError(
                "A data de fim da medição não "
                "pode ser anterior à data de início."
            )

        return data

    def create(self, validated_data):
        """Ao criar, atribui o usuário autenticado como created_by."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user

        instance = super().create(validated_data)

        # Registra no AuditLog
        if request and hasattr(request, "user"):
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.CREATE,
                model_name='Measurement',
                object_id=instance.id,
                object_display=str(instance),
                changes={},
            )

        return instance


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo Payment.

    Validações:
    - amount não pode ser negativo
    - amount não pode ser maior que measurement.value
    - só pode criar pagamento se measurement.status == APPROVED
    - não pode criar dois pagamentos para mesma medição
    """
    contract = serializers.PrimaryKeyRelatedField(
        queryset=Contract.objects.all(),
        required=False,
        allow_null=True
    )
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True
    )
    contract_title = serializers.SerializerMethodField(read_only=True)
    measurement_description = serializers.SerializerMethodField(read_only=True)
    anexo_nota_fiscal_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "contract",
            "contract_title",
            "measurement",
            "measurement_description",
            "created_by",
            "amount",
            "status",
            "paid_at",
            "numero_nota_fiscal",
            "data_emissao_nota",
            "valor_nota_fiscal",
            "anexo_nota_fiscal",
            "anexo_nota_fiscal_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "paid_at",
            "status",
            "contract_title",
            "measurement_description",
            "anexo_nota_fiscal_url",
        )

    def get_contract_title(self, obj):
        return obj.contract.title if obj.contract else None

    def get_measurement_description(self, obj):
        return obj.measurement.description if obj.measurement else None

    def get_anexo_nota_fiscal_url(self, obj):
        request = self.context.get('request')
        if obj.anexo_nota_fiscal and request:
            return request.build_absolute_uri(obj.anexo_nota_fiscal.url)
        return None

    def validate_amount(self, value):
        """Garante que o valor do pagamento é positivo."""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value

    def validate(self, data):
        """Validações cross-field."""
        measurement = data.get("measurement")

        if measurement:
            # Verifica se medição está APPROVED
            if measurement.status != Measurement.Status.APPROVED:
                raise serializers.ValidationError(
                    "Payment can only be created for APPROVED measurements"
                )

            # Verifica se amount não excede o valor da medição
            amount = data.get("amount")
            if amount and amount > measurement.value:
                raise serializers.ValidationError(
                    "Payment amount cannot exceed measurement value"
                )

            # Verifica se já existe pagamento para essa medição
            if measurement.payments.exists():
                raise serializers.ValidationError(
                    "A payment for this measurement already exists"
                )

        return data

    def create(self, validated_data):
        """Ao criar, atribui o usuário autenticado como created_by e
        preenche contract a partir de measurement."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user

        # Auto-preenche contract a partir de measurement
        measurement = validated_data.get("measurement")
        if measurement and not validated_data.get("contract"):
            validated_data["contract"] = measurement.contract

        # Default status é PENDING, pode ser alterado via ação
        instance = super().create(validated_data)

        # Registra no AuditLog
        if request and hasattr(request, "user"):
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.CREATE,
                model_name='Payment',
                object_id=instance.id,
                object_display=str(instance),
                changes={},
            )

        return instance


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer para logs de auditoria.

    Mostra o histórico completo de ações no sistema.
    Inclui: quem fez, o quê, quando, e quais dados mudaram.
    """
    username = serializers.CharField(
        source='user.username',
        read_only=True,
    )
    user_email = serializers.CharField(
        source='user.email',
        read_only=True,
    )

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'action',
            'model_name',
            'object_id',
            'object_display',
            'user',
            'username',
            'user_email',
            'changes',
            'timestamp',
            'ip_address',
        ]
        read_only_fields = fields
