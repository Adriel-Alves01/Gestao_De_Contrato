"""
Serviços de negócio para o módulo de contratos.

Responsáveis por conter a lógica de negócio isolada da API.
Podem ser chamados de views, CLI, tasks, etc.
"""
import logging
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import (
    Contract,
    ContractStatusHistory,
    Measurement,
    Payment,
    AuditLog,
)

logger = logging.getLogger('contracts')


class ContractService:
    """Serviço para operações em contratos."""

    @staticmethod
    @transaction.atomic
    def close_contract(contract, user):
        """Fecha um contrato e registra no histórico.

        Args:
            contract: Instância do Contract
            user: Usuário que está fazendo a ação

        Returns:
            contract: Contrato atualizado

        Raises:
            ValidationError: Se contrato já está fechado
        """
        logger.info(
            f"Attempting to close contract #{contract.id} "
            f"by user #{user.id}"
        )

        if contract.status == Contract.Status.CLOSED:
            logger.warning(
                f"Contract #{contract.id} already closed - "
                f"rejected by user #{user.id}"
            )
            raise ValidationError("Contract is already closed")

        old_status = contract.status
        contract.status = Contract.Status.CLOSED
        contract.save()

        # Registra mudança de status
        ContractStatusHistory.objects.create(
            contract=contract,
            old_status=old_status,
            new_status=contract.status,
            changed_by=user,
        )

        logger.info(
            f"Contract #{contract.id} closed successfully "
            f"by user #{user.id}"
        )

        return contract


class MeasurementService:
    """Serviço para operações em medições."""

    @staticmethod
    @transaction.atomic
    def approve_measurement(measurement, user):
        """Aprova uma medição e atualiza o saldo do contrato.

        Args:
            measurement: Instância do Measurement
            user: Usuário que está fazendo a ação

        Returns:
            measurement: Medição atualizada

        Raises:
            ValidationError: Se medição não pode ser aprovada
        """
        logger.info(
            f"Attempting to approve measurement #{measurement.id} "
            f"(value: {measurement.value}) by user #{user.id}"
        )

        if measurement.status == Measurement.Status.APPROVED:
            logger.warning(
                f"Measurement #{measurement.id} already approved"
            )
            raise ValidationError("Measurement is already approved")

        if measurement.status == Measurement.Status.REJECTED:
            logger.warning(
                f"Measurement #{measurement.id} was rejected, "
                f"cannot approve"
            )
            raise ValidationError(
                "Cannot approve a rejected measurement"
            )

        measurement.status = Measurement.Status.APPROVED
        measurement.approved_at = timezone.now()
        measurement.save()

        # Atualiza o saldo do contrato
        contract = measurement.contract
        old_balance = contract.remaining_balance
        contract.remaining_balance -= measurement.value
        contract.save()

        # Gera pagamento automaticamente para a medição aprovada
        Payment.objects.get_or_create(
            measurement=measurement,
            defaults={
                'contract': contract,
                'created_by': user,
                'amount': measurement.value,
                'status': Payment.Status.PENDING,
            },
        )

        # Regista no AuditLog
        AuditLog.objects.create(
            user=user,
            action=AuditLog.Action.APPROVE,
            model_name='Measurement',
            object_id=measurement.id,
            object_display=str(measurement),
            changes={'status': 'PENDING → APPROVED'},
        )

        logger.info(
            f"Measurement #{measurement.id} approved by user #{user.id} | "
            f"Contract #{contract.id} balance: "
            f"{old_balance} → {contract.remaining_balance}"
        )

        return measurement

    @staticmethod
    def reject_measurement(measurement, user):
        """Rejeita uma medição.

        Args:
            measurement: Instância do Measurement
            user: Usuário que está fazendo a ação

        Returns:
            measurement: Medição atualizada

        Raises:
            ValidationError: Se medição não pode ser rejeitada
        """
        logger.info(
            f"Attempting to reject measurement #{measurement.id} "
            f"by user #{user.id}"
        )

        if measurement.status == Measurement.Status.REJECTED:
            logger.warning(
                f"Measurement #{measurement.id} already rejected"
            )
            raise ValidationError("Measurement is already rejected")

        if measurement.status == Measurement.Status.APPROVED:
            raise ValidationError(
                "Cannot reject an approved measurement"
            )

        measurement.status = Measurement.Status.REJECTED
        measurement.rejected_at = timezone.now()
        measurement.save()

        # Registra no AuditLog
        AuditLog.objects.create(
            user=user,
            action=AuditLog.Action.REJECT,
            model_name='Measurement',
            object_id=measurement.id,
            object_display=str(measurement),
            changes={'status': 'PENDING → REJECTED'},
        )

        logger.info(
            f"Measurement #{measurement.id} rejected by user #{user.id}"
        )

        return measurement

    @staticmethod
    @transaction.atomic
    def reopen_measurement(measurement, user):
        """Reabre uma medição rejeitada (apenas ADMIN).

        Converte REJECTED → PENDING para permitir aprovação novamente.
        Registra a ação no AuditLog com detalhes da reversão.

        Args:
            measurement: Instância do Measurement
            user: Usuário ADMIN que está revertendo a rejeição

        Returns:
            measurement: Medição atualizada

        Raises:
            ValidationError: Se medição não está rejeitada
        """
        logger.info(
            f"Attempting to reopen measurement #{measurement.id} "
            f"(was REJECTED) by admin user #{user.id}"
        )

        if measurement.status != Measurement.Status.REJECTED:
            logger.warning(
                f"Measurement #{measurement.id} is not rejected - "
                f"cannot reopen"
            )
            raise ValidationError(
                "Cannot reopen a measurement that is not rejected"
            )

        measurement.status = Measurement.Status.PENDING
        measurement.rejected_at = None  # Limpa timestamp de rejeição
        measurement.save()

        # Registra no AuditLog
        AuditLog.objects.create(
            user=user,
            action=AuditLog.Action.REOPEN,
            model_name='Measurement',
            object_id=measurement.id,
            object_display=str(measurement),
            changes={'status': 'REJECTED → PENDING'},
        )

        logger.info(
            f"Measurement #{measurement.id} reopened by admin user #{user.id}"
        )

        return measurement


class PaymentService:
    """Serviço para operações em pagamentos."""

    @staticmethod
    @transaction.atomic
    def mark_as_paid(payment, user):
        """Marca um pagamento como pago.

        OBS: O saldo já foi decrementado quando a medição foi aprovada!
        Aqui apenas marcamos como PAID, não alteramos o saldo novamente.

        Args:
            payment: Instância do Payment
            user: Usuário que está fazendo a ação

        Returns:
            payment: Pagamento atualizado

        Raises:
            ValidationError: Se pagamento já está pago
        """
        logger.info(
            f"Attempting to mark payment #{payment.id} "
            f"(amount: {payment.amount}) as PAID by user #{user.id}"
        )

        if payment.status == Payment.Status.PAID:
            logger.warning(
                f"Payment #{payment.id} already marked as PAID"
            )
            raise ValidationError("Payment is already marked as paid")

        payment.status = Payment.Status.PAID
        payment.paid_at = timezone.now()
        payment.save()

        # Registra no AuditLog
        AuditLog.objects.create(
            user=user,
            action=AuditLog.Action.PAID,
            model_name='Payment',
            object_id=payment.id,
            object_display=str(payment),
            changes={'status': 'PENDING → PAID'},
        )

        logger.info(
            f"Payment #{payment.id} marked as PAID by user #{user.id} | "
            f"Contract #{payment.contract.id} | Amount: {payment.amount}"
        )

        return payment

    @staticmethod
    @transaction.atomic
    def mark_as_failed(payment, user):
        """Marca um pagamento como falho.

        Args:
            payment: Instância do Payment
            user: Usuário que está fazendo a ação

        Returns:
            payment: Pagamento atualizado

        Raises:
            ValidationError: Se pagamento não pode falhar
        """
        logger.info(
            f"Attempting to mark payment #{payment.id} as FAILED "
            f"by user #{user.id}"
        )

        if payment.status == Payment.Status.FAILED:
            logger.warning(
                f"Payment #{payment.id} already marked as FAILED"
            )
            raise ValidationError("Payment is already marked as failed")

        if payment.status == Payment.Status.PAID:
            logger.error(
                f"Cannot mark payment #{payment.id} as FAILED - "
                f"already PAID"
            )
            raise ValidationError(
                "Cannot mark a paid payment as failed"
            )

        payment.status = Payment.Status.FAILED
        payment.save()

        logger.info(
            f"Payment #{payment.id} marked as FAILED by user #{user.id}"
        )

        return payment
