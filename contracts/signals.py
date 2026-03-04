"""
Django Signals para auditoria automática.

Campos monitorados:
- Contract: status, title, remaining_balance
- Measurement: status, value
- Payment: status

Cada mudança gera um registro em AuditLog com:
- Quem mudou (user do request)
- O quê mudou (model, object_id, fields)
- Quando (timestamp)
- Como (before/after values)
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Contract, Measurement, Payment, AuditLog


def get_client_ip(request):
    """Extrai IP real do cliente (mesmo atrás de proxy)."""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_request_user():
    """
    Obtém usuário da request acessível globally.
    Nota: Em Django, isso é complicado sem middleware.
    Solução: Vamos registrar na view/serializer.
    """
    return None


@receiver(post_save, sender=Contract)
def log_contract_change(sender, instance, created, **kwargs):
    """Registra criação/atualização de contratos."""
    # Só registra se houver usuário logado (vamos passar via contexto na view)
    if not hasattr(instance, '_audit_user'):
        return

    action = AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE

    AuditLog.objects.create(
        user=instance._audit_user,
        action=action,
        model_name='Contract',
        object_id=instance.id,
        object_display=str(instance),
        changes=getattr(instance, '_audit_changes', {}),
        ip_address=getattr(instance, '_audit_ip', None),
    )


@receiver(post_save, sender=Measurement)
def log_measurement_change(sender, instance, created, **kwargs):
    """Registra criação/atualização/aprovação de medições."""
    if not hasattr(instance, '_audit_user'):
        return

    action = getattr(
        instance,
        '_audit_action',
        AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE
    )

    AuditLog.objects.create(
        user=instance._audit_user,
        action=action,
        model_name='Measurement',
        object_id=instance.id,
        object_display=str(instance),
        changes=getattr(instance, '_audit_changes', {}),
        ip_address=getattr(instance, '_audit_ip', None),
    )


@receiver(post_save, sender=Payment)
def log_payment_change(sender, instance, created, **kwargs):
    """Registra criação/atualização/pagamento de pagamentos."""
    if not hasattr(instance, '_audit_user'):
        return

    action = getattr(
        instance,
        '_audit_action',
        AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE
    )

    AuditLog.objects.create(
        user=instance._audit_user,
        action=action,
        model_name='Payment',
        object_id=instance.id,
        object_display=str(instance),
        changes=getattr(instance, '_audit_changes', {}),
        ip_address=getattr(instance, '_audit_ip', None),
    )
