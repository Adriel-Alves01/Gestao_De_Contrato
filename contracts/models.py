from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import JSONField

User = get_user_model()


class Contract(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        CLOSED = "CLOSED", "Closed"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    total_value = models.DecimalField(max_digits=15, decimal_places=2)
    remaining_balance = models.DecimalField(max_digits=15, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    manager = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="managed_contracts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="deleted_contracts",
    )

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["manager"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_deleted"]),
        ]

    def __str__(self):
        return self.title


class Measurement(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    contract = models.ForeignKey(
        Contract, on_delete=models.CASCADE, related_name="measurements"
    )
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="created_measurements"
    )
    description = models.TextField(blank=True)
    value = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["contract"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["approved_at"]),
        ]

    def __str__(self):
        return (
            f"Measurement #{self.id} - {self.contract.title} - "
            f"{self.status}"
        )


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"

    contract = models.ForeignKey(
        Contract, on_delete=models.PROTECT, related_name="payments"
    )
    measurement = models.ForeignKey(
        Measurement, on_delete=models.PROTECT, related_name="payments"
    )
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="created_payments"
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("measurement",)
        indexes = [
            models.Index(fields=["contract"]),
            models.Index(fields=["status"]),
            models.Index(fields=["paid_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return (
            f"Payment #{self.id} - {self.contract.title} - "
            f"{self.amount} - {self.status}"
        )


class Attachment(models.Model):
    contract = models.ForeignKey(
        Contract, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to="attachments/")
    uploaded_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="uploaded_attachments"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["contract"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Attachment #{self.id} - {self.contract.title}"


class ContractStatusHistory(models.Model):
    contract = models.ForeignKey(
        Contract, on_delete=models.CASCADE, related_name="status_history"
    )
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="status_changes"
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["contract"]),
            models.Index(fields=["changed_at"]),
        ]

    def __str__(self):
        return (
            f"Status change #{self.id} - {self.contract.title} - "
            f"{self.old_status} → {self.new_status}"
        )


class AuditLog(models.Model):
    """
    Registra TODAS as operações (CREATE, UPDATE, DELETE) no sistema.
    Essencial para compliance, rastreabilidade e análise de segurança.
    """
    class Action(models.TextChoices):
        CREATE = "CREATE", "Criado"
        UPDATE = "UPDATE", "Atualizado"
        DELETE = "DELETE", "Deletado (soft delete)"
        APPROVE = "APPROVE", "Aprovado"
        REJECT = "REJECT", "Rejeitado"
        REOPEN = "REOPEN", "Reaberto (Rejeição Revertida)"
        PAID = "PAID", "Marcado como Pago"
        FAILED = "FAILED", "Marcado como Falhou"
        RESTORE = "RESTORE", "Restaurado"

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    action = models.CharField(
        max_length=20,
        choices=Action.choices,
    )
    model_name = models.CharField(max_length=50)
    object_id = models.PositiveIntegerField()
    object_display = models.CharField(max_length=255, blank=True)
    # {"field": {"before": old_value, "after": new_value}}
    changes = JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["model_name", "object_id"]),
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
        ]

    def __str__(self):
        return (
            f"{self.action} {self.model_name}#{self.object_id} "
            f"by {self.user}"
        )
